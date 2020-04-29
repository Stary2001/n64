#!/usr/bin/env python3

# This file is Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# License: BSD

import os
import argparse
import sys

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

import litex_platform_n64
from litex.build.io import SDRTristate, SDRInput, DDROutput

from litex.soc.cores.clock import *
from litex.soc.cores.spi_flash import SpiFlash, SpiFlashSingle
from litex.soc.cores.gpio import GPIOIn, GPIOOut
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

from litex.build.generic_platform import *

from litedram.modules import IS42S16320
from litedram.phy import GENSDRPHY

from litex_clock import iCE40PLL_90deg

# IOs ----------------------------------------------------------------------------------------------

_gpios = [
    ("gpio", 0, Pins("j4:0"), IOStandard("LVCMOS33")),
    ("gpio", 1, Pins("j4:1"), IOStandard("LVCMOS33")),
]

# CRG ----------------------------------------------------------------------------------------------

class _CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.clock_domains.cd_sys = ClockDomain()
        self.clock_domains.cd_sys_ps = ClockDomain()
        self.clock_domains.cd_por = ClockDomain()
        # # #

        # Clk / Rst
        clk25 = platform.request("clk25")
        platform.add_period_constraint(clk25, 1e9/25e6)
        
        #if sys_clk_freq == 25e6:
        #    self.comb += self.cd_sys.clk.eq(clk25)
        #else:
        if True:
            # PLL
            self.submodules.pll = pll = iCE40PLL(primitive="SB_PLL40_PAD")

            pll.register_clkin(clk25, 25e6)
            pll.create_clkout(self.cd_sys, sys_clk_freq)
            #pll.create_clkout_90(self.cd_sys_ps, sys_clk_freq)

            platform.add_period_constraint(self.cd_sys.clk, sys_clk_freq)
            #platform.add_period_constraint(self.cd_sys_ps.clk, sys_clk_freq)

            self.specials += DDROutput(0, 1, platform.request("sdram_clock"), self.cd_sys.clk)

        # Power On Reset
        por_cycles  = 4096
        por_counter = Signal(log2_int(por_cycles), reset=por_cycles-1)
        self.comb += self.cd_por.clk.eq(self.cd_sys.clk)
        platform.add_period_constraint(self.cd_por.clk, 1e9/sys_clk_freq)
        self.sync.por += If(por_counter != 0, por_counter.eq(por_counter - 1))
        
        #self.specials += AsyncResetSynchronizer(self.cd_por, ~rst_n)
        self.specials += AsyncResetSynchronizer(self.cd_sys, (por_counter != 0) | ~pll.locked)

# n64 ----------------------------------------------------------------------------------------

kB = 1024
mB = 1024*kB
bios_flash_offset = 0x40000

class N64SoC(SoCCore):
    mem_map = {**SoCCore.mem_map, **{
        "spiflash": 0x20000000,  # (default shadow @0xa0000000)
    }}
    def __init__(self):
        platform     = litex_platform_n64.Platform()
        sys_clk_freq = int(48e6)

        kwargs = {}
        kwargs["clk_freq"] = sys_clk_freq
        kwargs["cpu_type"] = "vexriscv"
        kwargs["cpu_variant"] = "minimal"
        
        kwargs["integrated_rom_size"]  = 0
        kwargs["integrated_sram_size"] = 3*kB
        kwargs["cpu_reset_address"] = self.mem_map["spiflash"] + bios_flash_offset
        # SoCMini ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, **kwargs)

        if not self.integrated_main_ram_size:
            self.submodules.sdrphy = GENSDRPHY(platform.request("sdram"))
            self.add_sdram("sdram",
                phy                     = self.sdrphy,
                module                  = IS42S16320(sys_clk_freq, "1:1"),
                origin                  = self.mem_map["main_ram"],
                size                    = kwargs.get("max_sdram_size", 0x4000000),
                l2_cache_size           = kwargs.get("l2_size", 8192),
                l2_cache_min_data_width = kwargs.get("min_l2_data_width", 128),
                l2_cache_reverse        = True
            )

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq)

        self.submodules.spiflash = SpiFlash(platform.request("spiflash"), dummy=8, endianness="little")
        self.register_mem("spiflash", self.mem_map["spiflash"], self.spiflash.bus, size=8*mB)
        self.add_csr("spiflash")

        self.add_memory_region("rom", self.mem_map["spiflash"] + bios_flash_offset, 32*kB, type="cached+linker")

        # Led --------------------------------------------------------------------------------------
        self.submodules.led = GPIOOut(platform.request("io", 0))
        self.add_csr("led")

        #counter = Signal(32)
        #self.sync += counter.eq(counter + 1)
        #self.comb += platform.request("io",5).eq(counter[25])

        
        data_bus_oe = Signal()

        self.comb += data_bus_oe.eq(0)
        data_bus_ios = platform.request("n64_data")
        data_bus_in = Signal(16)
        data_bus_out = Signal(16)

        data_bus_oe_expanded = Signal(16)

        for i in range(0,16):
            self.comb += data_bus_oe_expanded[i].eq(data_bus_oe)
        self.specials += SDRTristate(io=data_bus_ios, i=data_bus_in, o=data_bus_out, oe=data_bus_oe_expanded)

        ale_l = Signal()
        ale_h = Signal()
        self.specials += SDRInput(i=platform.request("n64_ale_l", 0), o=ale_l)
        self.specials += SDRInput(i=platform.request("n64_ale_h", 0), o=ale_h)

        addr = Signal(32)
        
        self.sync += addr.eq(Cat(Mux(ale_l, data_bus_in[0:16], addr[0:16]), Mux(ale_h, data_bus_in[0:16], addr[16:32])))
        #self.sync += addr.eq(data_bus_in)

        # GPIOs ------------------------------------------------------------------------------------
        platform.add_extension(_gpios)
        self.submodules.gpio_addr = GPIOIn(addr)
        self.add_csr("gpio_addr")

# Load / Flash -------------------------------------------------------------------------------------

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="do the thing")
    parser.add_argument("--build",       action="store_true",      help="build bitstream")
    #parser.add_argument("--load",        action="store_true",      help="load bitstream")
    parser.add_argument("--flash",       action="store_true",      help="flash bitstream")
    args = parser.parse_args()

    soc     = N64SoC()
    builder = Builder(soc, output_dir="build", csr_csv="scripts/csr.csv")
    builder.build(build_name="n64", run=args.build)

    #if args.load:
    #    load()

    if args.flash:
        from litex.build.lattice.programmer import IceStormProgrammer
        prog = IceStormProgrammer()
        prog.flash(bios_flash_offset, "build/software/bios/bios.bin")
        prog.flash(0x00000000,        "build/gateware/n64.bin")

if __name__ == "__main__":
    main()