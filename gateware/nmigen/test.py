from nmigen import *
import math

class MockIO():
    def __init__(self, name, dir, width=1):
        if dir == "i" or dir == "io":
            self.i = Signal(width, name=name+"_i")
            self.i_clk = Signal(name=name+"_i_clk")

        if dir == "o" or dir == "io":
            self.o = Signal(width, name=name+"_o")
            self.o_clk = Signal(name=name+"_o_clk")

        if dir == "io":
            self.oe = Signal(name=name+"_oe")

class MockN64(Elaboratable):
    def __init__(self):
        self.ad = MockIO("n64_data", "io", 16)
        self.ale_h = MockIO("n64_ale_h", "i")
        self.ale_l = MockIO("n64_ale_l", "i")
        self.read = MockIO("n64_read", "i")
        self.write = MockIO("n64_write", "i")

    def elaborate(self, platform):
        m = Module()

        cur_addr = Signal(32)

        #         a         b      c  d     e
        #       <----><----------><-><--><----->
        # ale_l       -------------------
        # ____________|                 |_______
        #
        # ale_h -------------------
        # ______|                 |_____________
        # 
        # data
        #
        # _______AAAAAAAAAAAAAAAAAAAABBBBBB_____
        #

        ale_h = self.ale_h
        ale_l = self.ale_l
        read = self.read

        #dummy = Signal()

        counter = Signal(16)
        state = Signal(16)

        clk_period = 1/50e6
        delays = [1, 120, 80, 50, 50, 1040, 300, 60, 300, 60]
        # [11, 7, 3, 3, 52, 16, 4, 16, 4]
        delays = list(map(lambda a: math.ceil(a*1e-9/clk_period)-1, delays))
        import sys
        sys.stderr.write(str(delays)+"\n")
        delays = Array(delays)
        signals = Array([
            ale_h.i, # rise
            ale_l.i, # rise
            ale_h.i, # fall
            ale_h.i, # setup
            ale_l.i, # fall
            read.i,
            read.i,
            read.i,
            read.i,
            read.i])

        values = Array([1, 1, 0, 0, 0, 0, 1, 0, 1, 1])

        hi_addr = (cur_addr >> 16) & 0xffff
        lo_addr = cur_addr & 0xffff
        addrs = Array([hi_addr, hi_addr, hi_addr, lo_addr, lo_addr, lo_addr, lo_addr, lo_addr, lo_addr, lo_addr])

        if not (len(delays) == len(signals) == len(addrs) == len(values)):
            print("fug")
            print(len(delays), len(signals), len(addrs), len(values))
            exit()

        n64 = self

        with m.FSM() as fsm:
            with m.State("reset"):
                m.d.sync += [
                    self.ad.i.eq(0),
                    self.ale_h.i.eq(0),
                    self.write.i.eq(1),
                    self.read.i.eq(1),
                    self.ad.i.eq(0),
                    cur_addr.eq(0x10000000),
                    counter.eq(0)
                ]

                m.next = "wait"

            with m.State("wait"):
                with m.If(counter == delays[state]):
                    m.d.sync += signals[state].eq(values[state])
                    m.d.sync += n64.ad.i.eq(addrs[state])
                    m.d.sync += state.eq(state+1)

                    m.d.sync += counter.eq(0)
                    with m.If(state == len(delays)-1):
                        m.d.sync += state.eq(0)
                        m.d.sync += cur_addr.eq(cur_addr+4)
                    with m.Else():
                        m.d.sync += state.eq(state+1)
                with m.Else():
                    m.d.sync += counter.eq(counter+1)

        return m

    def ports(self):
        return [
            self.ad.i,
            self.ad.o,
            self.ad.oe,
            self.read.i,
            self.write.i,
            self.ale_l.i,
            self.ale_h.i
        ]


""" def drive_n64():
                yield n64.ale_l.i.eq(0)
                yield n64.ale_h.i.eq(0)
                yield n64.write.i.eq(1)
                yield n64.read.i.eq(1)
                yield n64.ad.i.eq(0)

                def delay(n):
                    for i in range(0,n):
                        yield

                def block_read(addr, n_bytes):
                    #         a    b  c
                    #       <----><--><-->
                    # ale_l       --------
                    # ____________|      |_________
                    #
                    # ale_h ----------
                    # ______|        |_____________
                    # 

                    a = 5
                    b = 10
                    c = 5

                    yield n64.ale_h.i.eq(1)
                    yield n64.ad.i.eq((addr >> 16) & 0xffff)
                    yield from delay(a)
                    yield n64.ale_l.i.eq(1)
                    yield from delay(b-3)
                    yield n64.ale_h.i.eq(0)
                    yield from delay(3)
                    yield n64.ad.i.eq(addr & 0xffff)
                    yield from delay(c)
                    yield n64.ale_l.i.eq(0)

                    yield from delay(100)

                    n = n_bytes//2
                    for i in range(0,n):
                        yield n64.read.i.eq(1)
                        yield from delay(5)
                        yield n64.read.i.eq(0)
                        yield from delay(15)

                yield from block_read(0x10000000, 4)

                for i in range(0x40, 0x1000, 4):
                    yield from block_read(0x10000000 + i, 4)

                for i in range(8, 0x40, 4):
                    yield from block_read(0x10000000 + i, 4)
"""