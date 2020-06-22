from litedram.common import *

sdram_module_nphases = {
    "SDR":   1,
    "DDR":   2,
    "LPDDR": 2,
    "DDR2":  2,
    "DDR3":  4,
    "DDR4":  4,
}

def get_sdram_phy_settings(memtype, data_width, clk_freq):
    nphases = sdram_module_nphases[memtype]

    if memtype == "SDR":
        # Settings from gensdrphy
        rdphase       = 0
        wrphase       = 0
        rdcmdphase    = 0
        wrcmdphase    = 0
        cl            = 2
        cwl           = None
        read_latency  = 4
        write_latency = 0
    elif memtype in ["DDR", "LPDDR"]:
        # Settings from s6ddrphy
        rdphase       = 0
        wrphase       = 1
        rdcmdphase    = 1
        wrcmdphase    = 0
        cl            = 3
        cwl           = None
        read_latency  = 5
        write_latency = 0
    elif memtype in ["DDR2", "DDR3"]:
        # Settings from s7ddrphy
        tck                 = 2/(2*nphases*clk_freq)
        cmd_latency         = 0
        cl, cwl             = get_cl_cw(memtype, tck)
        cl_sys_latency      = get_sys_latency(nphases, cl)
        cwl                 = cwl + cmd_latency
        cwl_sys_latency     = get_sys_latency(nphases, cwl)
        rdcmdphase, rdphase = get_sys_phases(nphases, cl_sys_latency, cl)
        wrcmdphase, wrphase = get_sys_phases(nphases, cwl_sys_latency, cwl)
        read_latency        = 2 + cl_sys_latency + 2 + 3
        write_latency       = cwl_sys_latency
    elif memtype == "DDR4":
        # Settings from usddrphy
        tck                 = 2/(2*nphases*clk_freq)
        cmd_latency         = 0
        cl, cwl             = get_cl_cw(memtype, tck)
        cl_sys_latency      = get_sys_latency(nphases, cl)
        cwl                 = cwl + cmd_latency
        cwl_sys_latency     = get_sys_latency(nphases, cwl)
        rdcmdphase, rdphase = get_sys_phases(nphases, cl_sys_latency, cl)
        wrcmdphase, wrphase = get_sys_phases(nphases, cwl_sys_latency, cwl)
        read_latency        = 2 + cl_sys_latency + 1 + 3
        write_latency       = cwl_sys_latency

    sdram_phy_settings = {
        "nphases":       nphases,
        "rdphase":       rdphase,
        "wrphase":       wrphase,
        "rdcmdphase":    rdcmdphase,
        "wrcmdphase":    wrcmdphase,
        "cl":            cl,
        "cwl":           cwl,
        "read_latency":  read_latency,
        "write_latency": write_latency,
    }

    return PhySettings(
        phytype       = "GENSDRPHY",
        memtype      = memtype,
        databits     = data_width,
        dfi_databits = data_width if memtype == "SDR" else 2*data_width,
        **sdram_phy_settings,
    )