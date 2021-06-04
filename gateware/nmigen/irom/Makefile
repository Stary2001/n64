O_FILES = irom.o main.o

%.o: %.c
	riscv64-unknown-elf-gcc -O2 -c -march=rv32i -mabi=ilp32 -nostdlib -nostartfiles $< -o $@

%.o: %.s
	riscv64-unknown-elf-gcc -c -march=rv32i -mabi=ilp32 -nostdlib -nostartfiles $< -o $@

irom.elf: $(O_FILES)
	riscv64-unknown-elf-ld -melf32lriscv -T irom.ld $^ -o $@

irom.bin: irom.elf
	riscv64-unknown-elf-objcopy -O binary $< $@
