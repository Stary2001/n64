#!/usr/bin/env python3

# This file is Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# License: BSD

import os
import argparse
import sys
import subprocess

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

import litex_platform_n64
from litex.build.io import SDRTristate, SDRInput, DDROutput

from litex.soc.cores.clock import *
from litex.soc.cores.spi_flash import SpiFlash, SpiFlashSingle
from litex.soc.cores.gpio import GPIOIn, GPIOOut
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.integration.common import *
from litex.soc.interconnect import wishbone
from litex.build.generic_platform import *

from litedram.modules import IS42S16320
from litedram.phy import GENSDRPHY

from litex_clock import iCE40PLL_90deg

# Simulation

from litex.build.sim.config import SimConfig
from litedram.phy.model import SDRAMPHYModel
from litex.soc.cores import uart

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

from sim import get_sdram_phy_settings

class N64SoC(SoCCore):
    mem_map = {**SoCCore.mem_map, **{
        "spiflash": 0x20000000,  # (default shadow @0xa0000000)
    }}

    def __init__(self, simulate, sdram_init=[], with_analyzer=False):

        self.simulate = simulate

        if simulate:
            platform = litex_platform_n64.N64SimPlatform()
        else:
            platform = litex_platform_n64.Platform()

        sys_clk_freq = int(48e6)

        kwargs = {}
        kwargs["clk_freq"] = sys_clk_freq
        kwargs["cpu_type"] = "vexriscv"
        kwargs["cpu_variant"] = "minimal"
        
        kwargs["integrated_rom_size"]  = 0
        kwargs["integrated_sram_size"] = 2*kB
        kwargs["cpu_reset_address"] = self.mem_map["spiflash"] + bios_flash_offset

        if simulate:
            kwargs["with_uart"] = False
            kwargs["with_ethernet"] = False

        # SoCMini ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, **kwargs)

        if simulate:
            self.submodules.uart_phy = uart.RS232PHYModel(platform.request("serial"))
            self.submodules.uart = uart.UART(self.uart_phy)
            self.add_csr("uart")
            self.add_interrupt("uart")
        if not self.integrated_main_ram_size:
            if simulate:
                sdram_data_width = 16
                sdram_module     = IS42S16320(sys_clk_freq, "1:1")
                phy_settings     = get_sdram_phy_settings(
                    memtype    = sdram_module.memtype,
                    data_width = sdram_data_width,
                    clk_freq   = sys_clk_freq)

                self.submodules.sdrphy = SDRAMPHYModel(sdram_module, phy_settings, init=sdram_init)

                self.add_constant("MEMTEST_DATA_SIZE", 8*1024)
                self.add_constant("MEMTEST_ADDR_SIZE", 8*1024)
            else:
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
        if simulate:
            self.submodules.crg = CRG(platform.request("sys_clk"))
        else:
            self.submodules.crg = _CRG(platform, sys_clk_freq)

        if simulate:
            integrated_rom_init = get_mem_data("build/software/bios/bios.bin", "little")

            self.add_rom("rom", self.cpu.reset_address, len(integrated_rom_init)*4, integrated_rom_init)
        else:
            self.submodules.spiflash = SpiFlash(platform.request("spiflash"), dummy=8, endianness="little")
            self.register_mem("spiflash", self.mem_map["spiflash"], self.spiflash.bus, size=8*mB)
            self.add_csr("spiflash")
            self.add_memory_region("rom", self.mem_map["spiflash"] + bios_flash_offset, 32*kB, type="cached+linker")


        # Led --------------------------------------------------------------------------------------
        self.submodules.led = GPIOOut(platform.request("io0"))
        self.add_csr("led")

        # GPIOs ------------------------------------------------------------------------------------

        self.submodules.gpio0 = GPIOOut(platform.request("io1"))
        self.add_csr("gpio0")
        self.submodules.gpio1 = GPIOOut(platform.request("io2"))
        self.add_csr("gpio1")
        platform.add_extension(_gpios)

        if with_analyzer:
            analyzer_signals = [
                self.cpu.ibus,
                self.cpu.dbus
            ]
            self.submodules.analyzer = LiteScopeAnalyzer(analyzer_signals, 512)
            self.add_csr("analyzer")


# Load / Flash -------------------------------------------------------------------------------------

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="do the thing")
    #parser.add_argument("--load",        action="store_true",      help="load bitstream")
    parser.add_argument("--flash",       action="store_true",      help="flash bitstream")
    parser.add_argument("--sim",       action="store_true",      help="simulate")
    parser.add_argument("--threads",   default=1,      help="simulate")
    parser.add_argument("--trace",              action="store_true",    help="Enable VCD tracing")
    parser.add_argument("--trace-start",        default=0,              help="Cycle to start VCD tracing")
    parser.add_argument("--trace-end",          default=-1,             help="Cycle to end VCD tracing")
    parser.add_argument("--opt-level",          default="O3",           help="Compilation optimization level")
    parser.add_argument("--sdram-init",          default=None,           help="SDRAM init file")

    args = parser.parse_args()

    sim_config = SimConfig(default_clk="sys_clk")
    sim_config.add_module("serial2console", "serial")

    build_kwargs = {}

    if args.sim:
        build_kwargs["threads"] = args.threads
        build_kwargs["sim_config"] = sim_config
        build_kwargs["opt_level"]   = args.opt_level
        build_kwargs["trace"]       = args.trace
        build_kwargs["trace_start"] = int(args.trace_start)
        build_kwargs["trace_end"]   = int(args.trace_end)

    soc = N64SoC(
        simulate=args.sim, 
        sdram_init     = [] if args.sdram_init is None else get_mem_data(args.sdram_init, "little"),
    )

    builder = Builder(soc, output_dir="build", csr_csv="scripts/csr.csv")
    builder.build(run=not (args.sim or args.flash), **build_kwargs)

    if args.flash:
        from litex.build.lattice.programmer import IceStormProgrammer
        prog = IceStormProgrammer()
        #prog.flash(4194304,        "sm64_swapped_half.n64")
        prog.flash(bios_flash_offset, "build/software/bios/bios.bin")
        prog.flash(0x00000000,        "build/gateware/litex_platform_n64.bin")

    if args.sim:
        builder.build(build=False, **build_kwargs)

if __name__ == "__main__":
    main()
