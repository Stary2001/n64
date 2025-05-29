from amaranth import *

class EdgeDetector(Elaboratable):
    def __init__(self, pin):
        self.pin = pin
        self.fall = Signal()
        self.rise = Signal()

    def elaborate(self, platform):
        m = Module()
        last = Signal()
        m.d.sync += [
            last.eq(self.pin),
            self.fall.eq(~self.pin & last),
            self.rise.eq(self.pin & ~last)
        ]

        return m
