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

        m.submodules.serv = Instance("serv_rf_top", **serv_args)

        return m

class PicoRV32(Elaboratable):
    def __init__(self):
        #self.timer_irq = Signal()
        
        a_width = 32
        d_width = 32

        self.bus = WishboneBus(d_width, a_width)

    def elaborate(self, platform):
        m = Module()

        if platform:
            platform.add_file("picorv32.v", open("picorv32/picorv32.v","r"))

        args = dict(
            i_wb_clk_i = ClockSignal(),
            i_wb_rst_i = ResetSignal(),
            #i_i_timer_irq = self.timer_irq,
            
            i_wbm_dat_i = self.bus.r_dat,
            i_wbm_ack_i = self.bus.ack,

            o_wbm_adr_o = self.bus.addr,
            o_wbm_dat_o = self.bus.w_dat,
            o_wbm_cyc_o = self.bus.cyc,
            o_wbm_stb_o = self.bus.stb,
            o_wbm_we_o = self.bus.we,
            o_wbm_sel_o = self.bus.sel
        )

        m.submodules.picorv32 = Instance("picorv32_wb", **args)

        return m