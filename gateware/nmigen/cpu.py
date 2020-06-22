from nmigen import *
import os
from wb import WishboneBus

class SERV(Elaboratable):
    def __init__(self):
        self.timer_irq = Signal()
        
        a_width = 32
        d_width = 32

        self.ibus = WishboneBus(d_width, a_width)
        self.dbus = WishboneBus(d_width, a_width)

    def elaborate(self, platform):
        m = Module()

        if platform:
            for file in os.listdir("serv/rtl/"):
                if file.endswith(".v"):
                  platform.add_file(file, open("serv/rtl/"+file,"r"))


        serv_args = dict(
            i_clk = ClockSignal(),
            i_i_rst = ResetSignal(),
            i_i_timer_irq = self.timer_irq,
            
            o_o_ibus_adr = self.ibus.addr,
            o_o_ibus_cyc = self.ibus.cyc,
            i_i_ibus_rdt = self.ibus.r_dat,
            i_i_ibus_ack = self.ibus.ack,
            # <we omitted>
            # <w_dat omitted>
            # <sel omitted>

            o_o_dbus_adr = self.dbus.addr,
            o_o_dbus_dat = self.dbus.w_dat,
            o_o_dbus_sel = self.dbus.sel,
            o_o_dbus_we  = self.dbus.we,
            o_o_dbus_cyc = self.dbus.cyc,
            i_i_dbus_rdt = self.dbus.r_dat,
            i_i_dbus_ack = self.dbus.ack,
        )

        #m.d.comb += self.ibus.stb.eq(self.ibus.cyc)
        #m.d.comb += self.dbus.stb.eq(self.dbus.cyc)

        """  (
        input wire         clk,
        input wire         i_rst,
        input wire         i_timer_irq,

        output wire [31:0] o_ibus_adr,
        output wire        o_ibus_cyc,
        input wire [31:0]  i_ibus_rdt,
        input wire         i_ibus_ack,
        output wire [31:0] o_dbus_adr,
        output wire [31:0] o_dbus_dat,
        output wire [3:0]  o_dbus_sel,
        output wire        o_dbus_we ,
        output wire        o_dbus_cyc,
        input wire [31:0]  i_dbus_rdt,
        input wire         i_dbus_ack"""

        m.submodules += Instance("serv_rf_top", **serv_args)

        return m