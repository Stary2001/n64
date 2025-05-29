O_FILES = irom.o main.o

all: irom.bin

%.o: %.c
	riscv32-unknown-elf-gcc -O2 -c -march=rv32i -mabi=ilp32 -nostdlib -nostartfiles $< -o $@

%.o: %.s
	riscv32-unknown-elf-gcc -c -march=rv32i -mabi=ilp32 -nostdlib -nostartfiles $< -o $@

irom.elf: $(O_FILES)
	riscv32-unknown-elf-ld -melf32lriscv -T irom.ld $^ -o $@

irom.bin: irom.elf
	riscv32-unknown-elf-objcopy -O binary $< $@
