.org 0

.extern main

.globl _start
_start:
li sp, 0x800

la a0, hello
jal uart_print_string 

jal spi_init

jal main
la a0, goodbye
jal uart_print_string 

.halt:
j .

# string pointer in a0
.globl uart_print_string
uart_print_string:
addi sp, sp, -4 
sw ra, 0(sp)

mv t0, a0

.loop:
lb a0, 0(t0)
beq a0, x0, .done
jal uart_print_char
addi t0, t0, 1
j .loop

.done:
lw ra, 0(sp)
add sp, sp, 4
jr ra

# char in a0
.globl uart_print_char
uart_print_char:
li a1, 0x10000000
li a2, 1

# wait until status == 1 (clear to send)
.loop2:
lb t1, 0(a1)
andi t1, t1, 1
bne t1, a2, .loop2

sb a0, 4(a1)

jr ra

.equ    SPI_BASE, 0x20000000
.equ    SPI_CSR,  4 * 0x00
.equ	SPI_RF,   4 * 0x03
spi_init:
	# Save return address
	# -------------------

	mv	t6, ra


	# Flash QSPI enable
	# -----------------

	li	t5, SPI_BASE

	li	t0, 0x00000004
	sw	t0, SPI_CSR(t5)

	li	t0, 0x00000002
	sw	t0, SPI_CSR(t5)

	# Wake flash (0xab)
	li	t0, 0xAB000000
	sw	t0, 0x40(t5)

	# Read and discard response
	lw	t0, SPI_RF(t5)

	# Release external control
	li	t0, 0x00000004
	sw	t0, SPI_CSR(t5)


	# Request external control
	li	t0, 0x00000004
	sw	t0, SPI_CSR(t5)

	li	t0, 0x00000002
	sw	t0, SPI_CSR(t5)

	# Enable QSPI (0x38)
	li	t0, 0x38000000
	sw	t0, 0x40(t5)

	# Read and discard response
	lw	t0, SPI_RF(t5)

	# Release external control
	li	t0, 0x00000004
	sw	t0, SPI_CSR(t5)


	# Flash QSPI config
	# not needed for the flash I have
	# -----------------

	# Request external control
	#li	t0, 0x00000004
	#sw	t0, SPI_CSR(t5)

	#li	t0, 0x00000002
	#sw	t0, SPI_CSR(t5)

	# Set QSPI parameters (dummy=6, wrap=64b)
	#li	t0, 0xc0230000
	#sw	t0, 0x74(t5)

	# Release external control
	#li	t0, 0x00000004
	#sw	t0, SPI_CSR(t5)

	# Return
	# ------

	mv	ra, t6
	ret


hello:
.asciz "Hello from IROM!\r\n"
goodbye:
.asciz "Goodbye from IROM!\r\n"
