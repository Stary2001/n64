YOSYS			= yosys
YOSYS_INCLUDE	= $(shell yosys-config --datdir)/include

SERV_V_FILES = external/serv/rtl/serv_shift.v external/serv/rtl/serv_bufreg.v external/serv/rtl/serv_alu.v external/serv/rtl/serv_csr.v external/serv/rtl/serv_ctrl.v external/serv/rtl/serv_decode.v external/serv/rtl/serv_mem_if.v external/serv/rtl/serv_rf_if.v external/serv/rtl/serv_rf_ram_if.v external/serv/rtl/serv_rf_ram.v external/serv/rtl/serv_state.v external/serv/rtl/serv_top.v external/serv/rtl/serv_rf_top.v
PICORV32_V_FILES = external/picorv32/picorv32.v
PHY_FILES = external/no2qpimem/rtl/qpi_memctrl.v external/no2qpimem/rtl/qpi_phy_ice40_1x.v external/no2misc/rtl/fifo_sync_shift.v external/no2misc/rtl/delay.v
SIM_CELLS = $(shell yosys-config --datdir)/ice40/cells_sim.v

V_FILES = verilog/cart_tb.v verilog/spiflash.v build/cart-sim.v external/sdram-model/sdr.v $(SERV_V_FILES) $(PICORV32_V_FILES) $(PHY_FILES) $(SIM_CELLS)
PY_FILES = cart.py cpu.py ice40_pll.py misc.py n64_board.py sdram.py test.py top.py uart.py wb.py
IVERILOG_FLAGS = -DWITH_SDRAM -DIVERILOG -Iexternal/sdram-model -Iexternal/serv/rtl -Dden512Mb -Dsg67 -Dx16 -g2012

build/cart-sim.v: $(PY_FILES) irom/irom.bin
	python top.py generate-top-sim > build/cart-sim.v

build/cart_tb: $(V_FILES)
	iverilog -o $@ $(IVERILOG_FLAGS) $^

build/cart_tb_cxxrtl: build/cart_tb.cpp cxxrtl/main.cpp
	g++ -I`yosys-config --datdir`/include -DTOP=\"../build/cart_tb.cpp\" -o $@ cxxrtl/main.cpp

build/cart_tb.cpp: $(V_FILES)
	$(YOSYS) cxxrtl/proc.ys

build/flash.bin:
	truncate --size 8M build/flash.bin
	dd if='Super Mario 64 (USA).n64' of=build/flash.bin conv=notrunc bs=4K oseek=48

build/flash.hex: build/flash.bin
	python make_hex.py build/flash.bin build/flash.hex

cart.vcd: build/cart_tb build/flash.hex
	./build/cart_tb

cart_cxxrtl.vcd: build/cart_tb_cxxrtl
	./build/cart_tb_cxxrtl cart_cxxrtl.vcd 2

irom/irom.bin: irom/irom.s irom/main.c
	make -C irom irom.bin

.PHONY: cart.vcd
all: cart.vcd
