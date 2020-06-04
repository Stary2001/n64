V_FILES = verilog/cart_tb.v build/cart-sim.v sdram/sdr.v
IVERILOG_FLAGS = -Isdram -Dden512Mb -Dsg67 -Dx16

# todo: proper migen dep tracking??
build/cart-sim.v: top.py sdram.py
	python top.py generate-top-sim > build/cart-sim.v

cart_tb: $(V_FILES)
	iverilog -o cart_tb $(IVERILOG_FLAGS) $(V_FILES)

cart.vcd: cart_tb
	./cart_tb

.PHONY: cart.vcd
all: cart.vcd
