import os
import struct

from amaranth import *
from misc import EdgeDetector

class Cart(Elaboratable):
    def __init__(self, sys_clk, sdram_port, trace):
        self.n64 = Record([
            ("ad_i", 16),
            ("ad_o", 16),
            ("ad_oe", 1),
            ("read", 1),
            ("write", 1),
            ("ale_l", 1),
            ("ale_h", 1)
            ])

        self.sdram_port = sdram_port
        self.sys_clk = sys_clk * 1e6

        self.trace_depth = trace.depth

        self.my_trace_addr = Signal(range(self.trace_depth))
        self.trace_addr = trace.addr
        self.trace_data = trace.data
        self.trace_en = trace.en

        self.buffer = Memory(depth=256, width=16)

    def elaborate(self, platform):
        m = Module()

        timer = Signal(23)
        m.d.sync += timer.eq(timer+1)

        addr = Signal(32)
        m.submodules.read_edge = read_edge = EdgeDetector(self.n64.read)
        m.submodules.ale_l_edge = ale_l_edge = EdgeDetector(self.n64.ale_l)

        m.submodules.buffer_rd = buffer_rd = self.buffer.read_port()
        m.submodules.buffer_wr = buffer_wr = self.buffer.write_port()

        m.d.sync += self.trace_en.eq(0)

        curr_block_start = Signal(32)
        do_sdram_read = Signal()

        # Read from memory whenever address changes.
        with m.If(self.n64.ale_l):
            with m.If(self.n64.ale_h):
                m.d.sync += addr[16:32].eq(self.n64.ad_i)
            with m.Else():
                m.d.sync += addr[0:16].eq(self.n64.ad_i)

        edge_counter = Signal(32)

        with m.If(ale_l_edge.fall):
            with m.If(addr >= curr_block_start+0x200):
                m.d.sync += [
                    # do thing
                    curr_block_start.eq(addr),
                    do_sdram_read.eq(1)
                ]
            m.d.sync += edge_counter.eq(edge_counter+1)

        with m.If(do_sdram_read):
            with m.FSM() as fsm:
                with m.State("wait_ack"):
                    m.d.sync += self.sdram_port.cmd.eq(3)
                    m.d.sync += self.sdram_port.addr.eq(curr_block_start&0xffffff)

                    with m.If(self.sdram_port.cmd_ack == 3):
                        m.d.sync += self.sdram_port.cmd.eq(0)
                        m.next = "read"
                with m.State("read"):
                    addr_counter = Signal(8)
                    read_began=Signal()
                    with m.If(self.sdram_port.rd_valid):
                        # transfer data
                        m.d.sync += [
                            read_began.eq(1),
                            buffer_wr.en.eq(1),
                            buffer_wr.addr.eq(addr_counter),
                            addr_counter.eq(addr_counter+1),
                            buffer_wr.data.eq(self.sdram_port.data_in)
                        ]
                    with m.Elif(read_began):
                        m.next = "done"
                with m.State("done"):
                    m.d.sync += do_sdram_read.eq(0)
                    m.next = "wait_ack"

        m.d.comb += buffer_rd.addr.eq(addr&0xff)

        with m.If(read_edge.fall):
            m.d.sync += self.n64.ad_oe.eq(1)
            m.d.comb += self.n64.ad_o.eq(buffer_rd.data)

            with m.If(self.trace_addr < (self.trace_depth-1)):
                m.d.sync += self.trace_en.eq(1)
                m.d.sync += self.trace_data.eq(Cat(addr, buffer_rd.data, Const(0, unsigned(16))))
                m.d.sync += self.trace_addr.eq(self.my_trace_addr)
                m.d.sync += self.my_trace_addr.eq(self.my_trace_addr+1)

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