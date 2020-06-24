from nmigen import *
from uart import UART

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
        m.submodules.wr = wr = backing.write_port()

        stb_delayed = Signal()

        m.d.comb += self.bus.r_dat.eq(0)
        with m.If(self.bus.cyc):
            with m.If(self.bus.we):
                m.d.sync += wr.addr.eq(self.bus.addr >> 2)
                m.d.sync += wr.data.eq(self.bus.w_dat)
                m.d.sync += wr.en.eq(1)
            with m.Else():
                m.d.sync += rd.addr.eq(self.bus.addr >> 2)
            m.d.sync += stb_delayed.eq(1)

        m.d.sync += self.bus.ack.eq(0)
        with m.If(stb_delayed):
            with m.If(~self.bus.we):
                m.d.comb += self.bus.r_dat.eq(rd.data)
            m.d.sync += self.bus.ack.eq(1)

        with m.If((self.bus.cyc == 0) & stb_delayed):
            m.d.sync += stb_delayed.eq(0)
            m.d.sync += self.bus.ack.eq(0)

        return m

class WishboneUART(Elaboratable):
    def __init__(self, divisor):
        self.uart = UART(divisor)
        self.bus = WishboneBus()

    def elaborate(self, platform):
        m = Module()
        m.submodules.uart = self.uart

        m.d.sync += self.bus.ack.eq(0)
        with m.If(self.bus.cyc):

            addr_mask = 4 - 1

            with m.If((self.bus.addr & addr_mask) == 0):
                m.d.sync += self.bus.ack.eq(1)
                m.d.sync += self.bus.r_dat.eq(0xdeadface)
            with m.Elif((self.bus.addr & addr_mask) == 4):
                m.d.sync += self.bus.ack.eq(1)
                m.d.sync += self.bus.r_dat.eq(0xc0ffee00)

        return m


class Peripheral:
    def __init__(self, dev, start, size):
        self.dev = dev
        self.bus = dev.bus

        self.addr = start
        self.size = size


class WishboneAddressDecoder(Elaboratable):
    def __init__(self, decodes, shift):
        self.decodes = decodes
        self.bus = WishboneBus()
        self.shift = shift

    def elaborate(self, platform):
        m = Module()

        bus=self.bus

        for d in self.decodes:
            with m.If((bus.addr >= Const(d.addr)) & (bus.addr < Const(d.addr + d.size))):
                m.d.comb += self.bus.connect_to(d.bus)

        return m