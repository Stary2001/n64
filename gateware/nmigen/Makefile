YOSYS			= yosys
YOSYS_INCLUDE	= $(shell yosys-config --datdir)/include

SERV_V_FILES =  serv/rtl/serv_shift.v serv/rtl/serv_bufreg.v serv/rtl/serv_alu.v serv/rtl/serv_csr.v serv/rtl/serv_ctrl.v serv/rtl/serv_decode.v serv/rtl/serv_mem_if.v serv/rtl/serv_rf_if.v serv/rtl/serv_rf_ram_if.v serv/rtl/serv_rf_ram.v serv/rtl/serv_state.v serv/rtl/serv_top.v serv/rtl/serv_rf_top.v
PICORV32_V_FILES = picorv32/picorv32.v
V_FILES = verilog/cart_tb.v build/cart-sim.v sdram/sdr.v $(SERV_V_FILES) $(PICORV32_V_FILES)
PY_FILES = cart.py cpu.py ice40_pll.py misc.py n64_board.py sdram.py test.py top.py uart.py wb.py
IVERILOG_FLAGS = -DWITH_SDRAM -DIVERILOG -Isdram -Iserv/rtl -Dden512Mb -Dsg67 -Dx16

build/cart-sim.v: $(PY_FILES) build/irom.bin
	python top.py generate-top-sim > build/cart-sim.v

build/cart_tb: $(V_FILES)
	iverilog -o $@ $(IVERILOG_FLAGS) $^

build/cart_tb_cxxrtl: build/cart_tb.cpp main.cpp
	g++ -I`yosys-config --datdir`/include -DTOP=\"build/cart_tb.cpp\" -o $@ main.cpp

build/cart_tb.cpp: $(V_FILES)
	$(YOSYS) proc.ys

cart.vcd: build/cart_tb
	./build/cart_tb

cart_cxxrtl.vcd: build/cart_tb_cxxrtl
	./build/cart_tb_cxxrtl cart_cxxrtl.vcd 2

build/irom.o: irom.s
	riscv64-unknown-elf-as -march=rv32i $< -o $@

build/irom.elf: build/irom.o
	riscv64-unknown-elf-ld -melf32lriscv $< -o $@

build/irom.bin: build/irom.elf
	riscv64-unknown-elf-objcopy -O binary $< $@

.PHONY: cart.vcd
all: cart.vcd
