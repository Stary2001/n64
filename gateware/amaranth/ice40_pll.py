#!/usr/bin/env nmigen

from collections import namedtuple
import warnings

from amaranth import *
from amaranth.lib.cdc import ResetSynchronizer
from amaranth.cli import main


class PLL(Elaboratable):

    """
    Instantiate the iCE40's phase-locked loop (PLL).

    This uses the iCE40's SB_PLL40_PAD primitive in simple feedback
    mode.

    The reference clock is directly connected to a package pin. To
    allocate that pin, request the pin with dir='-'; otherwise nMigen
    inserts an SB_IO on the pin.  E.g.,

        clk_pin = platform.request('clk12', dir='-')

    Because the PLL eats the external clock, that clock is not available
    for other uses.  So you might as well have the PLL generate the
    default 'sync' clock domain.

    This module also has a reset synchronizer -- the domain's reset line
    is not released until a few clocks after the PLL lock signal is
    good.
    """

    def __init__(self, freq_in_mhz, freq_out_mhz, domain_name='pll'):
        self.freq_in = freq_in_mhz
        self.freq_out = freq_out_mhz
        self.coeff = self._calc_freq_coefficients()
        self.clk_pin = Signal()
        self.domain_name = domain_name
        self.domain = ClockDomain(domain_name)
        self.ports = [
            self.clk_pin,
            self.domain.clk,
            self.domain.rst,
        ]

    def _calc_freq_coefficients(self):
        # cribbed from Icestorm's icepll.
        f_in, f_req = self.freq_in, self.freq_out
        assert 10 <= f_in <= 25
        #assert 16 <= f_req <= 275
        coefficients = namedtuple('coefficients', 'divr divf divq')
        divf_range = 128        # see comments in icepll.cc
        best_fout = float('inf')
        for divr in range(16):
            pfd = f_in / (divr + 1)
            if 10 <= pfd <= 133:
                for divf in range(divf_range):
                    vco = pfd * (divf + 1)
                    if 533 <= vco <= 1066:
                        for divq in range(1, 7):
                            fout = vco * 2**-divq
                            if abs(fout - f_req) < abs(best_fout - f_req):
                                best_fout = fout
                                best = coefficients(divr, divf, divq)
        if best_fout != f_req:
            warnings.warn(
                f'PLL: requested {f_req} MHz, got {best_fout} MHz)',
                stacklevel=3)
        return best

    def elaborate(self, platform):

        # coeff = self._calc_freq_coefficients()

        pll_lock = Signal()
        clk_out = Signal()
        pll = Instance("SB_PLL40_CORE",
            p_FEEDBACK_PATH='SIMPLE',
            p_DIVR=self.coeff.divr,
            p_DIVF=self.coeff.divf,
            p_DIVQ=self.coeff.divq,
            p_FILTER_RANGE=0b001,

            i_REFERENCECLK=self.clk_pin,
            i_RESETB=Const(1),
            i_BYPASS=Const(0),

            o_PLLOUTGLOBAL=clk_out,
            o_LOCK=pll_lock)

        m = Module()
        platform.add_clock_constraint(clk_out, self.freq_out * 1e6)
        m.d.comb += ClockSignal(self.domain_name).eq(clk_out)
        m.submodules += pll
        m.submodules += ResetSynchronizer(~pll_lock, domain=self.domain_name)
        return m


# There is no point in simulating this, but you can generate Verilog.

if __name__ == '__main__':
    pll = PLL(12, 30)
    main(pll, ports=pll.ports)
