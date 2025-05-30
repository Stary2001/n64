import os
import struct

from amaranth import *
import amaranth.lib.memory # as lib

from n64_board import *
from uart import UART
from ice40_pll import PLL
from wb import *
#from wb import WishboneRAM, WishboneUART, WishboneGPIO, WishboneAddressDecoder, Peripheral, WishboneSPIFlash, 
from cpu import SERV, PicoRV32
from cart import Cart
from sdram import SDRAMController, SDRAMArbiter

class Top(Elaboratable):
    def __init__(self, sys_clk, with_sdram, with_cpu, uart_baud=115200):
        self.sys_clk = sys_clk * 1e6
        self.with_sdram = with_sdram
        self.with_cpu = with_cpu
        self.uart_baud = uart_baud

        self.sdram = SDRAMController(self.sys_clk)
        self.sdram_arb = SDRAMArbiter(self.sdram)

        self.flash_trace = WishboneTrace(64, 256)
        self.cart_trace = WishboneTrace(64, 512)
        self.gpio = WishboneGPIO()
        self.timer = WishboneTimer()

        self.cart = Cart(sys_clk, self.sdram_arb.ports[1], self.cart_trace)
        if self.with_cpu == "serv":
            self.cpu = SERV()
        elif self.with_cpu == "picorv32":
            self.cpu = PicoRV32(debug=True)
        else:
            raise Exception("pls")
        
        #self.uart = UART(int(self.sys_clk//115200))
        self.buffer = amaranth.lib.memory.Memory(shape=unsigned(16), depth=256, init=[])
        self.wb_uart = WishboneUART(int(self.sys_clk//self.uart_baud))

        self.flash = WishboneSPIFlash()

    def elaborate(self, platform):
        m = Module()
        
        m.submodules.cart = self.cart
        m.submodules.cpu = self.cpu

        if self.with_sdram:
            #m.submodules.sdram_ctrl = self.sdram
            m.submodules.sdram_arb = self.sdram_arb

        with open("irom/irom.bin", "rb") as irom_file:
            irom_init = list(map(lambda a: a[0], struct.iter_unpack("<I",irom_file.read())))

        irom_init += [0xbeeffac0] * (512-len(irom_init))
        irom = WishboneRAM(init=irom_init)

        if self.with_cpu == "serv":
            drom_init = [0xbeeffac0] * (512)
            drom = WishboneRAM(init=irom_init)

            decoder = WishboneAddressDecoder(decodes = [
                Peripheral(drom, 0, 512 * 4),
                Peripheral(self.wb_uart, 0x10000000, 0x8),
            ])

            m.submodules.drom = drom
            m.d.comb += self.cpu.ibus.connect_to(irom.bus)
            m.d.comb += self.cpu.dbus.connect_to(decoder.bus)
        elif self.with_cpu == "picorv32":            
            decoder = WishboneAddressDecoder(decodes = [
                Peripheral(irom, 0, 512 * 4),
                Peripheral(self.wb_uart, 0x10000000, 0x8),
                Peripheral(self.flash, 0x20000000, 0x20*4),
                Peripheral(self.flash_trace, 0x30000000, self.flash_trace.depth*4),
                Peripheral(self.timer, 0x40000000, 4),
                Peripheral(self.gpio, 0x50000000, 4),
                Peripheral(self.cart_trace, 0x60000000, self.cart_trace.depth*4),
            ])

            m.d.comb += self.cpu.bus.connect_to(decoder.bus)

        m.submodules.irom = irom
        m.submodules.wb_uart = self.wb_uart
        m.submodules.decoder = decoder
        m.submodules.flash = self.flash
        m.submodules.flash_trace = self.flash_trace
        m.submodules.cart_trace = self.cart_trace
        m.submodules.timer = self.timer
        m.submodules.gpio = self.gpio

        data = Signal(16)

        write_happened = Signal()
        read_happened = Signal()

        # Things get a bit wacky here - the address is in 16bit words.
        dram_addr = Signal(25)
        flash_addr = Signal(24)
        flash_offset = 0x30_000

        buffer_w = self.buffer.write_port()
        buffer_r = self.buffer.read_port(transparent_for=(buffer_w,))
        buffer_full = Signal()

        m.d.comb += buffer_r.addr.eq(dram_addr & 0xff)
        m.d.comb += buffer_w.addr.eq(flash_addr & 0xff)

        m.submodules += self.buffer

        #m.submodules.uart = uart = self.uart

        # Read from SPI flash into SDRAM on startup
        # buffer -> SDRAM
        if self.with_sdram:
            sdram_rd = self.sdram_arb.ports[0]

            m.d.comb += sdram_rd.data_out.eq(0xffff)
            with m.FSM() as fsm:
                with m.State("wait_full"):
                    with m.If(buffer_full):
                        m.next = "wait_sdram"
                with m.State("wait_sdram"):
                    m.d.sync += [
                        sdram_rd.cmd.eq(1),
                        sdram_rd.addr.eq(dram_addr)
                    ]

                    with m.If(sdram_rd.cmd_ack == 1):
                        m.d.sync += sdram_rd.cmd.eq(0)
                        #m.d.sync += dram_addr.eq(0)
                        m.next = "write"
                with m.State("write"):
                    m.d.comb += sdram_rd.data_out.eq(buffer_r.data)
                    m.d.sync += sdram_rd.addr.eq(dram_addr)
                    
                    with m.If(sdram_rd.wr_valid):
                        m.d.sync += write_happened.eq(1)
                        m.d.sync += dram_addr.eq(dram_addr+1)

                        #m.d.comb += sdram_rd.data_out.eq(buffer_r.data)
                    with m.Else():
                        with m.If(write_happened):
                            m.d.sync += write_happened.eq(0)
                            m.next = "done"
                with m.State("done"):
                    m.d.sync += buffer_full.eq(0)
                    #m.d.sync += dram_addr.eq(0)
                    m.next = "wait_full"

            m.d.sync += self.flash.mi.valid.eq(0)
            m.d.sync += buffer_w.en.eq(0)

            self.trace_depth = self.flash_trace.depth
            self.my_trace_addr = Signal(range(self.trace_depth))
            self.trace_addr = self.flash_trace.addr
            self.trace_data = self.flash_trace.data
            self.trace_en = self.flash_trace.en
            m.d.sync += self.trace_en.eq(0)

            # SPI flash -> read buffer
            with m.FSM() as fsm:
                with m.State("wait"):
                    counter = Signal(32)

                    m.d.sync += buffer_full.eq(0)
                    # Firmware writes to io 0 when SPI flash is setup
                    with m.If(self.gpio.io[0] == 1):
                        m.next = "wait_ready"
                    with m.Else():
                        m.d.sync += counter.eq(counter+1)
                with m.State("wait_ready"):
                    with m.If(self.flash.mi.ready & ~buffer_full):
                        m.d.sync += [
                            self.flash.mi.valid.eq(1),
                            self.flash.mi.rw.eq(1),
                            self.flash.mi.len.eq(64), # adjust this for time to first read ...
                            self.flash.mi.addr.eq((flash_addr<<1) + flash_offset)
                        ]
                        m.next = "mi_read"
                with m.State("mi_read"):
                    data = Signal(32)
                    with m.If(self.flash.mi.rlast):
                        with m.If((flash_addr & 0xff) == 0):
                            m.d.sync += buffer_full.eq(1)

                        m.next = "wait_ready"
                    with m.Elif(self.flash.mi.rstb):
                        m.d.sync += [
                            buffer_w.data.eq(self.flash.mi.rdata[16:32]),
                            data.eq(self.flash.mi.rdata),
                            buffer_w.en.eq(1)
                        ]
                        m.next = "mi_read_2"
                with m.State("mi_read_2"):
                    m.d.sync += [
                        buffer_w.data.eq(data[0:16]),
                        flash_addr.eq(flash_addr+1),
                        buffer_w.en.eq(1)
                    ]

                    with m.If(self.trace_addr < (self.trace_depth-1)):
                        m.d.sync += self.trace_data.eq(Cat(Const(0x00, unsigned(8)), flash_addr, data))
                        m.d.sync += self.trace_en.eq(1)
                        m.d.sync += self.my_trace_addr.eq(self.my_trace_addr+1)
                        m.d.sync += self.trace_addr.eq(self.my_trace_addr)

                    m.next = "mi_read_3"
                with m.State("mi_read_3"):
                    m.d.sync += [
                        flash_addr.eq(flash_addr+1),
                    ]
                    m.next = "mi_read"
        return m

    def ports(self):
        return self.cart.ports()


class CartConcrete(Elaboratable):
    def __init__(self, sys_clk, uart_baud, uart_delay):
        self.sys_clk = sys_clk
        self.uart_baud = uart_baud
        self.uart_delay = uart_delay

    def elaborate(self, platform):
        m = Module()

        n64 = platform.request("n64", xdr={'ad': 1, 'read': 1, 'write': 1, 'ale_l': 1, 'ale_h': 1, 'cold_reset': 1, 'nmi': 1 })

        sdram = platform.request("sdram", xdr = 
            { 
                'clk': 2,
                'clk_en': 1,
                'cs': 1,
                'we': 1,
                'ras': 1,
                'cas': 1,
                'ba': 1,
                'a': 1,
                'dq': 1,
                'dqm': 1
            }
        )

        uart_tx = platform.request("io",6)
        uart_tx_reg = Signal()
        uart_rx = platform.request("io",7)
        uart_rx_reg = Signal()

        extra = platform.request("io", 5)
        extra2 = platform.request("io", 4)
        m.d.comb += [
            extra.oe.eq(1),
            extra2.oe.eq(1),
            extra.o.eq(n64.read.i),
            extra2.o.eq(0),
        ]

        top = Top(self.sys_clk, with_sdram=True, with_cpu = "picorv32", uart_baud = self.uart_baud)
        cart = top.cart

        m.d.sync += [
            uart_rx_reg.eq(uart_rx.i),
            uart_tx_reg.eq(top.wb_uart.uart.tx_o)
        ]

        m.d.comb += [
            uart_tx.oe.eq(1),
            uart_rx.oe.eq(0),
            uart_tx.o.eq(uart_tx_reg),
            top.wb_uart.uart.rx_i.eq(uart_rx_reg)
        ]

        clk = ClockSignal("sync")
        m.d.comb += [
            n64.read.i_clk.eq(clk),
            n64.write.i_clk.eq(clk),
            n64.ale_l.i_clk.eq(clk),
            n64.ale_h.i_clk.eq(clk),
            n64.ad.i_clk.eq(clk),
            n64.ad.o_clk.eq(clk),
            n64.cold_reset.i_clk.eq(clk),
            n64.nmi.i_clk.eq(clk)
        ]

        m.d.comb += [
            sdram.dq.o.eq(cart.n64.ad_o),

            n64.ad.oe.eq(cart.n64.ad_oe),

            cart.n64.ad_i.eq(n64.ad.i),
            cart.n64.read.eq(n64.read.i),
            cart.n64.write.eq(n64.write.i),
            cart.n64.ale_l.eq(n64.ale_l.i),
            cart.n64.ale_h.eq(n64.ale_h.i),
        ]

        clk = ClockSignal()
        sdram_ctrl = top.sdram.sdram
        m.d.comb += [
            sdram.clk.o0.eq(0),
            sdram.clk.o1.eq(1),
            sdram.clk.o_clk.eq(clk),

            sdram.clk_en.o.eq(sdram_ctrl.cke),
            sdram.clk_en.o_clk.eq(clk),

            sdram.cs.o.eq(sdram_ctrl.cs),
            sdram.cs.o_clk.eq(clk),

            sdram.we.o.eq(sdram_ctrl.we),
            sdram.we.o_clk.eq(clk),

            sdram.ras.o.eq(sdram_ctrl.ras),
            sdram.ras.o_clk.eq(clk),

            sdram.cas.o.eq(sdram_ctrl.cas),
            sdram.cas.o_clk.eq(clk),

            sdram.a.o.eq(sdram_ctrl.addr),
            sdram.a.o_clk.eq(clk),

            sdram.ba.o.eq(sdram_ctrl.ba),
            sdram.ba.o_clk.eq(clk),

            sdram.dqm.o.eq(sdram_ctrl.dqm),
            sdram.dqm.o_clk.eq(clk),

            sdram_ctrl.data_in.eq(sdram.dq.i),
            sdram.dq.o.eq(sdram_ctrl.data_out),
            sdram.dq.oe.eq(sdram_ctrl.data_oe),

            sdram.dq.i_clk.eq(clk),
            sdram.dq.o_clk.eq(clk),
        ]

        m.submodules.top = top

        return m

class CartConcretePLL(CartConcrete):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def elaborate(self, platform):
        m = Module()
        clk_pin = ClockSignal("sync")

        pll = PLL(freq_in_mhz=25, freq_out_mhz=self.sys_clk)
        m.domains += pll.domain
        m.submodules += [pll]
        m.d.comb += [
            pll.clk_pin.eq(clk_pin),
        ]
        cap = super().elaborate(platform)
        m.submodules.top = DomainRenamer({'sync': 'pll'})(cap)
        return m

from test import MockN64
class CartSim(Elaboratable):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        kwargs["with_sdram"] = True
        kwargs["with_cpu"] = "picorv32"

        self.uart_tx = Signal()
        self.uart_rx = Signal()

        self.n64 = MockN64()
        self.top = Top(*self.args, **self.kwargs)

    def elaborate(self, platform):
        m = Module()
        m.submodules.sim_wrapper = self.top

        cart = self.top.cart
        n64 = self.n64

        m.d.comb += [
            n64.ad.o.eq(cart.n64.ad_o),
            n64.ad.oe.eq(cart.n64.ad_oe),

            cart.n64.ad_i.eq(n64.ad.i),
            cart.n64.read.eq(n64.read.i),
            cart.n64.write.eq(n64.write.i),
            cart.n64.ale_l.eq(n64.ale_l.i),
            cart.n64.ale_h.eq(n64.ale_h.i),

            self.top.wb_uart.uart.rx_i.eq(1)
        ]
        m.submodules.n64 = n64

        if self.top.with_sdram:
            sdram_io = self.top.sdram.sdram
            m.submodules.sdram_sim = Instance("sdr_wrapper",
                i_dq_in = sdram_io.data_out,
                o_dq_out = sdram_io.data_in,
                i_dq_oe = sdram_io.data_oe,
                i_Addr = sdram_io.addr,
                i_Ba = sdram_io.ba,
                i_Clk = ClockSignal(),
                i_Cke = sdram_io.cke,
                i_Cs_n = ~sdram_io.cs,
                i_Ras_n = ~sdram_io.ras,
                i_Cas_n = ~sdram_io.cas,
                i_We_n = ~sdram_io.we,
                i_Dqm = sdram_io.dqm)

        return m

    def ports(self):
        return []

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "generate-top":
            from amaranth.back import rtlil, verilog

            top = Top(sys_clk=0.5)
            print(verilog.convert(top, ports=top.ports(), name="top"))
        if sys.argv[1] == "generate-top-sim":
            from amaranth.back import rtlil, verilog

            top = CartSim(sys_clk=0.5)
            print(verilog.convert(top, ports=top.ports(), name="top"))
        elif sys.argv[1] == "sim":
            cart = CartSim(sys_clk=50)
            n64 = cart.n64

            from amaranth.back import pysim

            sim = pysim.Simulator(cart)
            ports = [n64.ale_h.i, cart.n64.ale_l.i, n64.read.i, n64.write.i, n64.ad.i, n64.ad.o]

            with sim.write_vcd(vcd_file=open("/tmp/cart.vcd", "w"),
                    gtkw_file=open("/tmp/cart.gtkw", "w"),
                    traces=ports):
                sim.add_clock(1/50e6)

                def do_nothing():
                    for i in range(0, 10000):
                        yield

                sim.add_sync_process(do_nothing)
                sim.run()
    else:
        platform = N64Platform()
        concrete = CartConcretePLL(sys_clk = 50, uart_baud = 115200, uart_delay = 10000)
        platform.build(concrete, read_verilog_opts="-I../external/serv/rtl", do_program=True)