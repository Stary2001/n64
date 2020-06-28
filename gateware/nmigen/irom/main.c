extern void uart_print_char(char c);
extern void uart_print_string(char *c);

const char *str = "Hello from C!\r\n";

int main() {
	uart_print_string(str);
	return 0;
}