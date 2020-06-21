from litex.build.generic_platform import *
from litex.build.lattice import LatticePlatform
from litex.build.lattice.programmer import IceStormProgrammer

from litex.build.sim import SimPlatform

# IOs ----------------------------------------------------------------------------------------------

_io = [
    ("serial", 0,
        Subsignal("rx", Pins("45")),
        Subsignal("tx", Pins("44"), Misc("PULLUP")),
        IOStandard("LVCMOS33")
    ),

    ("spiflash", 0,
        Subsignal("cs_n", Pins("71"), IOStandard("LVCMOS33")),
        Subsignal("clk",  Pins("70"), IOStandard("LVCMOS33")),
        Subsignal("miso", Pins("68"), IOStandard("LVCMOS33")),
        Subsignal("mosi", Pins("67"), IOStandard("LVCMOS33")),
        Subsignal("wp",   Pins("62"), IOStandard("LVCMOS33")),
        Subsignal("hold", Pins("61"), IOStandard("LVCMOS33")),
    ),

    ("spiflash4x", 0,
        Subsignal("cs_n", Pins("71"), IOStandard("LVCMOS33")),
        Subsignal("clk",  Pins("70"), IOStandard("LVCMOS33")),
        Subsignal("dq",   Pins("67 68 62 61"), IOStandard("LVCMOS33")),
    ),

    ("sdram_clock", 0, Pins("113"), IOStandard("LVCMOS33")),
    ("sdram", 0,
        #Subsignal("clk", Pins("113")),
        Subsignal("a", Pins(
            "93 94 95 96 97 98 99 101 102 104 105 106 107")),
        Subsignal("dq", Pins(
            "135 134 130 129 128 125 124 122 136 137 138 139 141 142 143 144")),
        Subsignal("we_n",  Pins("116")),
        Subsignal("ras_n", Pins("114")),
        Subsignal("cas_n", Pins("115")),
        Subsignal("cs_n", Pins("110")), # gnd
        Subsignal("cke",  Pins("112")), # 3v3
        Subsignal("ba",    Pins("90 91")),
        Subsignal("dm",   Pins("118 117")), # gnd
        IOStandard("LVCMOS33"),
    ),

    ("io0",    0, Pins("37"), IOStandard("LVCMOS33")),
    ("io1",    0, Pins("38"), IOStandard("LVCMOS33")),
    ("io2",    0, Pins("39"), IOStandard("LVCMOS33")),
    ("io3",    0, Pins("41"), IOStandard("LVCMOS33")),
    ("io4",    0, Pins("42"), IOStandard("LVCMOS33")),
    ("io5",    0, Pins("43"), IOStandard("LVCMOS33")),

    ("extra_io", 0, Pins("73"), IOStandard("LVCMOS33")),
    ("extra_io", 1, Pins("75"), IOStandard("LVCMOS33")),
    ("extra_io", 2, Pins("78"), IOStandard("LVCMOS33")),
    ("extra_io", 3, Pins("80"), IOStandard("LVCMOS33")),
    ("extra_io", 4, Pins("82"), IOStandard("LVCMOS33")),
    ("extra_io", 5, Pins("84"), IOStandard("LVCMOS33")),
    ("extra_io", 6, Pins("87"), IOStandard("LVCMOS33")),
    ("extra_io", 7, Pins("88"), IOStandard("LVCMOS33")),

    ("n64_data", 0, Pins("23 21 19 17 9 7 3 1 2 4 8 10 18 20 22 24"), IOStandard("LVCMOS33")),
    ("n64_ale_l", 0, Pins("15"), IOStandard("LVCMOS33")),
    ("n64_ale_h", 0, Pins("11"), IOStandard("LVCMOS33")),
    ("n64_read", 0, Pins("12"), IOStandard("LVCMOS33")),
    ("n64_write", 0, Pins("16"), IOStandard("LVCMOS33")),

    # was 52
    ("clk25", 0, Pins("49"), IOStandard("LVCMOS33"))
]

# Connectors ---------------------------------------------------------------------------------------

_connectors = [
]

# Platform -----------------------------------------------------------------------------------------

class Platform(LatticePlatform):
    default_clk_name   = "clk25"
    default_clk_period = 1e9/25e6

    def __init__(self):
        LatticePlatform.__init__(self, "ice40-hx8k-tq144:4k", _io, _connectors, toolchain="icestorm")

    def create_programmer(self):
        return IceStormProgrammer()

_sim_io = [
    ("sys_clk", 0, Pins(1)),
    ("sys_rst", 0, Pins(1)),
    ("serial", 0,
        Subsignal("source_valid", Pins(1)),
        Subsignal("source_ready", Pins(1)),
        Subsignal("source_data",  Pins(8)),

        Subsignal("sink_valid",   Pins(1)),
        Subsignal("sink_ready",   Pins(1)),
        Subsignal("sink_data",    Pins(8)),
    ),

    ("io0", 0, Pins(1)),
    ("io1", 0, Pins(1)),
    ("io2", 0, Pins(1)),

    ("n64_data", 0, Pins(16)),
    ("n64_ale_l", 0, Pins(1)),
    ("n64_ale_h", 0, Pins(1)),
    ("n64_read", 0, Pins(1)),
    ("n64_write", 0, Pins(1))
]

# Platform -----------------------------------------------------------------------------------------

class N64SimPlatform(SimPlatform):
    def __init__(self):
        SimPlatform.__init__(self, "SIM", _sim_io)