.org 0

.extern main

.globl _start
_start:
li sp, 0x200

la a0, hello
jal uart_print_string 
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

hello:
.asciz "Hello from IROM!\r\n"
goodbye:
.asciz "Goodbye from IROM!\r\n"
