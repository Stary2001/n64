from nmigen import *
from uart import UART

class MemoryInterface(Record):
    def __init__(self, n_cs=1, data_width=32, addr_width=24):
        super().__init__([
            ("cs", n_cs),
            ("addr", addr_width),
            ("len", 7),
            ("rw", 1),
            ("valid", 1),
            ("ready", 1),
            
            ("wdata", data_width),
            ("wack", 1),
            ("wlast", 1),
            
            ("rdata", data_width),
            ("rstb", 1),
            ("rlast", 1)
            ])

class WishboneBus(Record):
    def __init__(self, data_width=32, addr_width=32):
        super().__init__([
            ("cyc", 1),
            ("stb", 1),
            ("ack", 1),
            ("we", 1),
            ("sel", data_width//8),
            ("addr", addr_width),
            ("r_dat", data_width),
            ("w_dat", data_width)
            ])

        """o_o_ibus_adr = self.ibus.addr,
            o_o_ibus_cyc = self.ibus.cyc,
            i_i_ibus_rdt = self.ibus.r_dat,
            i_i_ibus_ack = self.ibus.ack,"""

    # connect cpu bus "input" -> rom "output"   
    # bus.connect_to(rom)

    def connect_to(self, other):
        return [
            other.cyc.eq(self.cyc),
            other.stb.eq(self.stb),
            other.sel.eq(self.sel),
            other.we.eq(self.we),
            other.addr.eq(self.addr),
            other.w_dat.eq(self.w_dat),

            self.ack.eq(other.ack),
            self.r_dat.eq(other.r_dat)
        ]

class WishboneRAM(Elaboratable):
    def __init__(self, init):
        self.init = init
        self.bus = WishboneBus()

    def elaborate(self, platform):
        m = Module()

        backing = Memory(width=32, depth=len(self.init), init=self.init)
        m.submodules.rd = rd = backing.read_port()
        m.submodules.wr = wr = backing.write_port(granularity=8)

        stb_delayed = Signal()

        m.d.comb += wr.addr.eq(self.bus.addr >> 2)
        m.d.comb += rd.addr.eq(self.bus.addr >> 2)
        m.d.comb += wr.data.eq(self.bus.w_dat)
        m.d.comb += self.bus.r_dat.eq(rd.data)

        m.d.sync += self.bus.ack.eq(self.bus.cyc & ~self.bus.ack)

        passthrough_wr = Signal()
        m.d.sync += passthrough_wr.eq((self.bus.cyc & self.bus.we) & ~passthrough_wr)
        m.d.comb += wr.en.eq(Mux(passthrough_wr, 0, self.bus.sel))
        return m

class WishboneTrace(Elaboratable):
    def __init__(self, width, depth):
        self.bus = WishboneBus()

        self.width = width
        self.depth = depth

        self.backing = Memory(width=width, depth=depth)

        self.addr = Signal(range(depth))
        self.data = Signal(width)
        self.en = Signal()

    def elaborate(self, platform):
        m = Module()

        backing = self.backing
        m.submodules.rd = rd = backing.read_port()
        m.submodules.wr = wr = backing.write_port()

        m.d.comb += wr.en.eq(self.en)
        m.d.comb += wr.addr.eq(self.addr)
        m.d.comb += wr.data.eq(self.data)

        m.d.comb += rd.addr.eq(self.bus.addr >> 3)
        m.d.comb += self.bus.r_dat.eq(rd.data.word_select(self.bus.addr[2], 32))
        m.d.sync += self.bus.ack.eq(self.bus.cyc & ~self.bus.ack)
        return m

class WishboneTimer(Elaboratable):
    def __init__(self, width=32):
        self.bus = WishboneBus()
        self.timer = Signal(width)

    def elaborate(self, platform):
        m = Module()

        m.d.sync += self.timer.eq(self.timer+1)

        m.d.comb += self.bus.r_dat.eq(self.timer)
        m.d.sync += self.bus.ack.eq(self.bus.cyc & ~self.bus.ack)
        return m


class WishboneUART(Elaboratable):
    """
        TODO add a small fifo?
        maybe, it seems to work alright without.
    """
    def __init__(self, divisor):
        self.uart = UART(divisor)
        self.bus = WishboneBus()

    def elaborate(self, platform):
        m = Module()
        m.submodules.uart = self.uart

        m.d.sync += self.uart.tx_rdy.eq(0)

        ack = Signal()
        m.d.comb += self.uart.rx_ack.eq(ack)
        
        with m.If(~self.uart.rx_rdy):
            m.d.sync += ack.eq(0)

        with m.If(self.bus.cyc):
            addr_mask = 8 - 1
            with m.If((self.bus.addr & addr_mask) == 0):
                m.d.sync += self.bus.r_dat.eq(Cat(self.uart.tx_ack, self.uart.rx_rdy & ~ack, self.uart.rx_err, self.uart.rx_ovf))
            with m.Elif((self.bus.addr & addr_mask) == 4):
                with m.If(self.bus.we): # write
                    m.d.sync += [
                        self.uart.tx_data.eq(self.bus.w_dat[0:8]),
                        self.uart.tx_rdy.eq(1)
                    ]
                with m.Else():
                    m.d.sync += [
                        self.bus.r_dat.eq(self.uart.rx_data),
                        ack.eq(1)
                    ]

        # drop ack on second cycle
        m.d.sync += self.bus.ack.eq(self.bus.cyc & ~self.bus.ack)

        return m

class WishboneGPIO(Elaboratable):
    def __init__(self):
        self.bus = WishboneBus()
        #self.io = Array(8)

    def elaborate(self, platform):
        m = Module()

        """backing = Memory(width=32, depth=len(self.init), init=self.init)
        m.submodules.rd = rd = backing.read_port()
        m.submodules.wr = wr = backing.write_port(granularity=8)

        stb_delayed = Signal()

        m.d.comb += wr.addr.eq(self.bus.addr >> 2)
        m.d.comb += rd.addr.eq(self.bus.addr >> 2)
        m.d.comb += wr.data.eq(self.bus.w_dat)
        m.d.comb += self.bus.r_dat.eq(rd.data)

        m.d.sync += self.bus.ack.eq(self.bus.cyc & ~self.bus.ack)"""

        return m

class Peripheral:
    def __init__(self, dev, start, size):
        self.dev = dev
        self.bus = dev.bus

        self.addr = start
        self.size = size


class WishboneAddressDecoder(Elaboratable):
    def __init__(self, decodes):
        self.decodes = decodes
        self.bus = WishboneBus()

    def elaborate(self, platform):
        m = Module()

        bus=self.bus

        for d in self.decodes:
            with m.If((bus.addr >= Const(d.addr)) & (bus.addr < Const(d.addr + d.size))):
                m.d.comb += self.bus.connect_to(d.bus)

        return m

class WishboneSPIFlash(Elaboratable):
    def __init__(self):
        self.bus = WishboneBus()
        self.mi = MemoryInterface()

    def elaborate(self, platform):
        m = Module()

        bus = self.bus

        phy_io_i = Signal(4)
        phy_io_o = Signal(4)
        phy_io_oe = Signal(4)
        phy_clk_o = Signal()
        phy_cs_o = Signal()

        if platform:
            flash = platform.request("spi_flash_4x", dir={"cs": "-", "clk": "-", "dq": "-"})

            platform.add_file("qspi_master.v", open("ice40-playground/cores/qspi_master/rtl/qspi_master.v", "r"))
            platform.add_file("qspi_phy_ice40_1x.v", open("ice40-playground/cores/qspi_master/rtl/qspi_phy_ice40_1x.v", "r"))
            platform.add_file("misc.v", open("ice40-playground/cores/misc/rtl/fifo_sync_shift.v", "r"))
            platform.add_file("delay.v", open("ice40-playground/cores/misc/rtl/delay.v", "r"))

            pad_cs = flash.cs
            pad_clk = flash.clk
            pad_dq = flash.dq
        else:
            pad_cs = Signal()
            pad_clk = Signal()
            pad_dq = Signal(4)

            m.submodules.spiflash = Instance("spiflash",
                i_csb = pad_cs,
                i_clk = pad_clk,
                io_io0 = pad_dq[0],
                io_io1 = pad_dq[1],
                io_io2 = pad_dq[2],
                io_io3 = pad_dq[3]
            )

        cs_n = Signal()
        m.d.comb += pad_cs.eq(cs_n)

        m.submodules.phy = Instance("qspi_phy_ice40_1x",
            p_N_CS = 1,
            p_WITH_CLK = 1,
            p_NEG_IN = 0,

            io_pad_io = pad_dq,
            o_pad_clk = pad_clk,
            o_pad_cs_n = cs_n,

            o_phy_io_i = phy_io_i,
            i_phy_io_o = phy_io_o,
            i_phy_io_oe = phy_io_oe,
            i_phy_clk_o = phy_clk_o,
            i_phy_cs_o = phy_cs_o,

            i_clk = ClockSignal()
        )

        mi = self.mi

        m.d.comb += mi.cs.eq(0)

        m.submodules.qspi = Instance("qspi_master",
            p_N_CS = 1,
            p_CMD_READ = 0xEB,
            p_CMD_WRITE = 0x02,
            p_DUMMY_CLK = 8,
            p_PHY_DELAY = 2,

            i_phy_io_i = phy_io_i,
            o_phy_io_o = phy_io_o,
            o_phy_io_oe = phy_io_oe,
            o_phy_clk_o = phy_clk_o,
            o_phy_cs_o = phy_cs_o,

            i_mi_valid = mi.valid,
            i_mi_addr_cs = mi.cs,
            i_mi_addr = mi.addr,
            i_mi_len = mi.len,
            i_mi_rw = mi.rw,
            o_mi_ready = mi.ready,

            i_mi_wdata = mi.wdata,
            o_mi_wack = mi.wack,
            o_mi_wlast = mi.wlast,

            o_mi_rdata = mi.rdata,
            o_mi_rstb = mi.rstb,
            o_mi_rlast = mi.rlast,

            i_wb_addr = (self.bus.addr & 0x7f) >> 2,
            i_wb_wdata = self.bus.w_dat,
            o_wb_rdata = self.bus.r_dat,
            i_wb_we = self.bus.we,
            i_wb_cyc = self.bus.cyc,
            o_wb_ack = self.bus.ack,

            i_clk = ClockSignal(),
            i_rst = ResetSignal()
        )

        return m