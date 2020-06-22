V_FILES = verilog/cart_tb.v build/cart-sim.v sdram/sdr.v serv/rtl/serv_shift.v serv/rtl/serv_bufreg.v serv/rtl/serv_alu.v serv/rtl/serv_csr.v serv/rtl/serv_ctrl.v serv/rtl/serv_decode.v serv/rtl/serv_mem_if.v serv/rtl/serv_rf_if.v serv/rtl/serv_rf_ram_if.v serv/rtl/serv_rf_ram.v serv/rtl/serv_state.v serv/rtl/serv_top.v serv/rtl/serv_rf_top.v
IVERILOG_FLAGS = -Isdram -Iserv/rtl -Dden512Mb -Dsg67 -Dx16

# todo: proper migen dep tracking??
build/cart-sim.v: top.py sdram.py
	python top.py generate-top-sim > build/cart-sim.v

cart_tb: $(V_FILES)
	iverilog -o cart_tb $(IVERILOG_FLAGS) $(V_FILES)

cart.vcd: cart_tb
	./cart_tb

.PHONY: cart.vcd
all: cart.vcd
