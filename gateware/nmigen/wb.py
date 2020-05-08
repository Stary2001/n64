from nmigen import *

class WishboneBus(Elaboratable):
    def __init__(self):
        self.cyc = Signal()
        self.stb = Signal()
        self.ack = Signal()
        self.we = Signal()
        self.sel = Signal(4)

        self.addr = Signal(32) # width
        self.dat_r = Signal(32)

    def elaborate(self, platform):
        m=Module()
        return m

class WishboneMaster(Elaboratable):
    def __init__(self):
        self.bus = WishboneBus()
        self.addr_in = Signal(32)
        self.data = Signal(32)
        self.read = Signal()
        self.ready = Signal()

    def elaborate(self, platform):
        m = Module()
        m.submodules += self.bus

        m.d.comb += [
            self.bus.sel.eq(0b1111)
        ]

        self.bus_addr_start = Signal(32, reset=0x40000000)
        # 0x40000000 dram
        # 0x20000000 spiflash

        #m.d.sync += self.wb.stb.eq(0)
        with m.FSM() as fsm:
            with m.State("idle"):
                with m.If(self.read):
                    # start bus cycle
                    m.d.sync += [
                        self.bus.addr.eq((self.addr_in + self.bus_addr_start)>>2),
                        self.bus.we.eq(0),
                        self.bus.cyc.eq(1),
                        self.bus.stb.eq(1),

                        self.ready.eq(0)
                    ]
                    m.next = "wait_ack"
            with m.State("wait_ack"):
                with m.If(self.bus.ack):
                    m.d.sync += [
                        self.data.eq(self.bus.dat_r),
                        self.ready.eq(1),

                        self.bus.stb.eq(0),
                        self.bus.cyc.eq(0)
                    ]
                    m.next = "idle"
        return m