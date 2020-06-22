from nmigen import *

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

class WishboneROM(Elaboratable):
    def __init__(self, init):
        self.bus = WishboneBus()
        self.init = init

    def elaborate(self, platform):
        m = Module()

        backing = Memory(width=32, depth=len(self.init), init=self.init)
        m.submodules.rd = rd = backing.read_port()

        stb_delayed = Signal()

        m.d.sync += self.bus.r_dat.eq(0)
        with m.If(self.bus.cyc):
            m.d.sync += rd.addr.eq(self.bus.addr)
            m.d.sync += stb_delayed.eq(1)

        m.d.sync += self.bus.ack.eq(0)
        with m.If(stb_delayed):
            m.d.sync += self.bus.r_dat.eq(rd.data)
            m.d.sync += self.bus.ack.eq(1)

        with m.If((self.bus.cyc == 0) & stb_delayed):
            m.d.sync += stb_delayed.eq(0)
            m.d.sync += self.bus.ack.eq(0)

        return m