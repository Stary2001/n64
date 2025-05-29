`timescale 1ns/1ps

//`define den512Mb
//`define sg67
//`define x16
//`include "dram/sdr.v"

`ifdef WITH_SDRAM
module sdr_wrapper(dq_in, dq_out, dq_oe, Addr, Ba, Clk, Cke, Cs_n, Ras_n, Cas_n, We_n, Dqm);
    `include "external/sdram-model/sdr_parameters.vh"

    input                         Clk;
    input                         Cke;
    input                         Cs_n;
    input                         Ras_n;
    input                         Cas_n;
    input                         We_n;
    input     [ADDR_BITS - 1 : 0] Addr;
    input       [BA_BITS - 1 : 0] Ba;

    input [DQ_BITS - 1 : 0] dq_in;
    output [DQ_BITS - 1 : 0] dq_out;
    input dq_oe;

    wire [DQ_BITS - 1 : 0] dq;
    
    assign dq = dq_oe ? dq_in : 16'hzzzz; 
    assign dq_out = dq_oe ? 16'hzzzz : dq;

    input       [DM_BITS - 1 : 0] Dqm;

    sdr real_sdram(dq, Addr, Ba, ~Clk, Cke, Cs_n, Ras_n, Cas_n, We_n, Dqm);
endmodule
`endif

module tb_top();
  reg clk;
  reg rst;

// module sdr (Dq, Addr, Ba, Clk, Cke, Cs_n, Ras_n, Cas_n, We_n, Dqm);
 wire [3:0] dq;

 top top(rst, qspi_dq, clk);

`ifdef IVERILOG
 initial
 begin
    $dumpfile("cart.vcd");
    $dumpvars(0, top);

    clk = 0;
    rst = 0;

    #5  rst = 1;
    #50 rst = 0;

    #1000000 $finish();
 end

 always 
    #10 clk = !clk;
`endif
endmodule
