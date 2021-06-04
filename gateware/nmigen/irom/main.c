#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

extern void uart_print_char(char c);
extern void uart_print_string(const char *c);

const char *str = "Hello from C!\r\n";

char uart_read() {
	volatile uint32_t *uart_base = (volatile uint32_t*) 0x10000000;
	while(!((*uart_base)&2));
	return (char) (*(uart_base+1))&0xff;
}

char itoa_buffer[9];

char i_to_hex(int a) {
	if(a <= 9) {
		return '0' + a;
	}
	else {
		return 'a' + (a-10);
	}
}

const char* my_itoa(uint32_t n) {
	int i = 0;

	while(n!=0) {
		itoa_buffer[i++] = i_to_hex(n & 0xf);
		n = n >> 4;
	}

	while(i < 8) { itoa_buffer[i++]='0'; }

	itoa_buffer[i] = 0;
	i--;

    int j = 0;

    char ch;
    while (i > j)
    {
        ch = itoa_buffer[i];
        itoa_buffer[i] = itoa_buffer[j];
        itoa_buffer[j] = ch;
        i--;
        j++;
    }

	return itoa_buffer;
}

uint32_t read_timer(){ 
	return *((volatile uint32_t*)0x40000000);
}

/*
uint32_t flash_reg_read(uint32_t a){ 
	return *((volatile uint32_t*)0x20000000 + a);
}

void flash_reg_write(uint32_t a, uint32_t b){ 
	*((volatile uint32_t*)(0x20000000) + a) = b;
}

void flash_begin() {
	flash_reg_write(0, 4);
	flash_reg_write(0, 2);
}
void flash_end() {
	flash_reg_write(0, 4);
}

void spi_xfer(uint8_t *tx_data, size_t tx_len, size_t dummy_len, uint8_t *rx_data, size_t rx_len) { 
	size_t l = tx_len + dummy_len + rx_len;
	size_t a = 0;
	flash_begin();
	while(l>0) {
		int c;
		int s;

		if(l>=4) {
			c = 0x13;
			s = 0;
		} else {
			c = 0x10+l-1;
			s = 8*(4-l);
		}
		
		flash_reg_write(c, tx_data[a]);
		uint32_t data_out = flash_reg_read(3);
		//memcpy(&data_out);
		uart_print_string(my_itoa(data_out));
		a += 1;
		l-=4;
	}
	flash_end();
}*/

int main() {
	uint32_t start_time = read_timer();

	volatile uint32_t *uart_base = (volatile uint32_t*) 0x10000000;
	uart_print_string(str);
	while(true) {
		/*char c = uart_read();
		if(c == '\r') {
			uart_print_char('\r');
			uart_print_char('\n');
		}
		else {
			uart_print_char(c);
		}

		if((*uart_base) & 4) {
			uart_print_string("err\n");
		}*/


		if(*((volatile uint32_t*)0x30000000) != 0) {
			uint32_t end_time = read_timer();

			for(int i= 0 ;i<256; i++) {
				uart_print_string("Trace: ");
				uart_print_string(my_itoa(*(((volatile uint32_t*)0x30000000)+i)));
				uart_print_string(" after ");
				uart_print_string(my_itoa(end_time-start_time));
				uart_print_string("\r\n");
			}

			break;
		} else {
			//uart_print_string("alive\r\n");
		}

		//-for(int i =0;i<1000000;i++);
	}
	return 0;
}