import os
import subprocess

from nmigen.build import *
from nmigen.vendor.lattice_ice40 import *
from nmigen_boards.resources import *
import tempfile

__all__ = ["N64Platform"]

""""""

"""Resource("ftdi_clk", 0, Pins("49", dir="i"),
            Clock(60e6), Attrs(GLOBAL=True, IO_STANDARD="SB_LVCMOS")
        ),

        SDRAMResource(0,
            clk="113", cke="112", cs="110", we="116", ras="114", cas="115",
            ba="90 91", a="93 94 95 96 97 98 99 101 102 104 105 106 107",
            dq="135 134 130 129 128 125 124 122 138 139 141 142 143 144",
            dqm="118 117", attrs=Attrs(IO_STANDARD="SB_LVCMOS")
        ),

        # todo: check mosi/miso ordering...
        *SPIFlashResources(0,
            cs="71", clk="70", mosi="67", miso="68", wp="62", hold="61",
            attrs=Attrs(IO_STANDARD="SB_LVCMOS")
        ),"""

"""

Resource("ftdi", 0, 
    Subsignal("data", Pins("73 74 75 76 78 79 80 81", dir="io")),
    Subsignal("rxf", Pins("82", dir="i")), #C0
    Subsignal("txe", Pins("83", dir="i")), #C1
    Subsignal("rd", Pins("84", dir="o")), #C2
    Subsignal("wr", Pins("85", dir="o")), #C3
    Subsignal("siwua", Pins("87", dir="o")), #C4
    #Subsignal("clkout", Pins("49")), #C5
    Subsignal("oe", Pins("88", dir="o")), #C6
),"""

class N64Platform(LatticeICE40Platform):
    device      = "iCE40HX4K"
    package     = "TQ144"
    default_clk = "clk25"

    resources   = [
        Resource("clk25", 0, Pins("52", dir="i"),
            Clock(25e6), Attrs(GLOBAL=True, IO_STANDARD="SB_LVCMOS")
        ),

        *SPIFlashResources(0, clk="70", cipo="68", copi="67", cs_n="71", wp_n="62", hold_n="61"),

        #Resource("extra_io", 0, Pins("37 38 39 41 42 43 44 45", dir="io")),
        Resource("io", 0, Pins("37", dir="io")),
        Resource("io", 1, Pins("38", dir="io")),
        Resource("io", 2, Pins("39", dir="io")),
        Resource("io", 3, Pins("41", dir="io")),
        Resource("io", 4, Pins("42", dir="io")),
        Resource("io", 5, Pins("43", dir="io")),
        Resource("io", 6, Pins("44", dir="io")),
        Resource("io", 7, Pins("45", dir="io")),

        Resource("io", 15, Pins("73", dir="io")),
        Resource("io", 14, Pins("75", dir="io")),
        Resource("io", 13, Pins("78", dir="io")),
        Resource("io", 12, Pins("80", dir="io")),
        Resource("io", 11, Pins("82", dir="io")),
        Resource("io", 10, Pins("84", dir="io")),
        Resource("io", 9, Pins("87", dir="io")),
        Resource("io", 8, Pins("88", dir="io")),

        Resource("n64", 0, 
            Subsignal("ad", Pins("23 21 19 17 9 7 3 1 2 4 8 10 18 20 22 24", dir="io")),
            Subsignal("read", Pins("12", dir="i")),
            Subsignal("write", Pins("16", dir="i")),
            Subsignal("ale_l", Pins("15", dir="i")),
            Subsignal("ale_h", Pins("11", dir="i")),
        ),

        SDRAMResource(0,
            clk = "113",
            cke = "112",
            cs_n = "110",
            we_n = "116",
            ras_n = "114",
            cas_n = "115",

            ba = "90 91",
            a = "93 94 95 96 97 98 99 101 102 104 105 106 107",
            dq = "135 134 130 129 128 125 124 122 136 137 138 139 141 142 143 144",
            dqm = "118 117",

            attrs = Attrs(IO_STANDARD = "SB_LVCMOS")
        ),
    ]

    connectors  = [
    ]

    def toolchain_program(self, products, name):
        iceprog = os.environ.get("ICEPROG", "iceprog")
        with products.extract("{}.bin".format(name)) as bitstream_filename:
            subprocess.check_call([iceprog, bitstream_filename])

if __name__ == "__main__":
    from .test.blinky import *
    N64Platform().build(Blinky(), do_program=True)

