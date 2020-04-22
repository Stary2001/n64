from litex.build.generic_platform import *
from litex.build.lattice import LatticePlatform
from litex.build.lattice.programmer import IceStormProgrammer

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
        Subsignal("ba",    Pins("90 91")), # sdram pin a11 is ba
        Subsignal("dm",   Pins("118 117")), # gnd
        IOStandard("LVCMOS33"),
    ),

    ("io",    0, Pins("37"), IOStandard("LVCMOS33")),
    ("io",    1, Pins("38"), IOStandard("LVCMOS33")),
    ("io",    2, Pins("39"), IOStandard("LVCMOS33")),
    ("io",    3, Pins("41"), IOStandard("LVCMOS33")),
    ("io",    4, Pins("42"), IOStandard("LVCMOS33")),
    ("io",    5, Pins("43"), IOStandard("LVCMOS33")),

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
