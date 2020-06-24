import os
import struct

from nmigen import *
from misc import EdgeDetector

class Cart(Elaboratable):
    def __init__(self, sys_clk):
        self.n64 = Record([
            ("ad_i", 16),
            ("ad_o", 16),
            ("ad_oe", 1),
            ("read", 1),
            ("write", 1),
            ("ale_l", 1),
            ("ale_h", 1)
            ])

        self.sys_clk = sys_clk * 1e6

    def elaborate(self, platform):
        m = Module()

        timer = Signal(23)
        m.d.sync += timer.eq(timer+1)

        addr = Signal(32)
        m.submodules.read_edge = read_edge = EdgeDetector(self.n64.read)
        m.submodules.ale_l_edge = ale_l_edge = EdgeDetector(self.n64.ale_l)

        # Read from memory whenever address changes.
        with m.If(self.n64.ale_l):
            with m.If(self.n64.ale_h):
                m.d.sync += addr[16:32].eq(self.n64.ad_i)
            with m.Else():
                m.d.sync += addr[0:16].eq(self.n64.ad_i)

        with m.If(ale_l_edge.fall):
            # TODO possible optimization: check if addr is in the right range.
            m.d.sync += [
                
            ]

        with m.If(read_edge.fall):
            m.d.sync += self.n64.ad_oe.eq(1)
            # TODO data
            m.d.sync += self.n64.ad_o.eq(0)
            m.d.sync += addr.eq(addr+2)
        with m.Else():
            m.d.sync += self.n64.ad_oe.eq(0)

        return m

    def ports(self):
        return [
            self.n64.ad_i,
            self.n64.ad_o,
            self.n64.ad_oe,
            self.n64.read,
            self.n64.write,
            self.n64.ale_l,
            self.n64.ale_h,
        ]