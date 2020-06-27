.org 0

.globl _start
_start:
la a0, string
jal uart_print_string 

.done:
j .

uart_print_string:
mv t0, a0

.loop:
lb a0, 0(t0)
beq a0, x0, .done
jal uart_print_char
addi t0, t0, 1
j .loop

jr ra

# char in a0
uart_print_char:
li a1, 0x10000000
sb a0, 4(a1)
#lb t1, 0(t0)
jr ra

string:
.asciz "Hello World!"
