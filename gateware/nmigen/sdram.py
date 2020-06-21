from nmigen import *
import math

class SDRAMController(Elaboratable):
	def __init__(self, sys_clk):
		self.sdram = Record([
			("cke", 1),
			("cs", 1),
			("we", 1),
			("ras", 1),
			("cas", 1),
			("addr", 13),
			("ba", 2),
			("dqm", 2),
			("data_in", 16),
			("data_out", 16),
			("data_oe", 1)])

		self.bank_bits = 2
		self.row_bits = 13
		self.col_bits = 10

		# 0 = nop, 1 = read short, 2 = read long, 3 = write long
		self.cmd = Signal(2)
		self.cmd_ack = Signal(2)

		self.data_in = Signal(16)
		self.data_out = Signal(16)

		self.addr = Signal(self.bank_bits + self.row_bits + self.col_bits)

		# rd and wr valid go high _1 cycle_ before actual valid.
		self.rd_valid = Signal()
		self.wr_valid = Signal()

		self.sys_clk = sys_clk


	def elaborate(self, platform):
		m = Module()

		bank_bits = 2
		row_bits = 13
		col_bits = 10

		t_init = int(250e-6 * self.sys_clk)
		t_refresh = math.floor((32e-3/8192) * self.sys_clk)
		#print(t_refresh)

		t_rp = 3
		t_rc = 10
		t_rcd = 3 # todo calculate
		#t_mrd = 2
		t_mrd = 200
		cas = 3

		ram = self.sdram

		init_done = Signal()

		m.d.sync += [
			ram.addr.eq(0),
			ram.ba.eq(0),
		]

		cmd = Signal(4)
		m.d.comb += Cat(ram.we, ram.cas, ram.ras, ram.cs).eq(~cmd)
		#with m.If(init_done):
		m.d.sync += cmd.eq(0b0111) # n_CS low - nop
		#with m.Else():
		#	m.d.sync += cmd.eq(0b1111) # n_CS high - deassert
		
		# Initial cke/dqm states.
		
		refresh_timer = Signal(range(0,t_refresh*2))
		# always tick the refresh timer
		m.d.sync += refresh_timer.eq(refresh_timer+1)

		with m.FSM() as inner:
			with m.State("wait"):

				m.d.sync += self.sdram.cke.eq(0)
				m.d.sync += self.sdram.dqm.eq(0b11)

				counter = Signal(16)

				with m.If(counter < t_init):
					m.d.sync += counter.eq(counter+1)
				with m.Else():
					m.d.sync += self.sdram.cke.eq(1)
					m.next = "precharge"
			
			with m.State("precharge"):
				counter = Signal(4)
				with m.If(counter == 0):
					# cmd
					m.d.sync += [
						cmd.eq(0b0010),
						ram.addr.eq(1<<10)
					]
				with m.If(counter < t_rp):
					m.d.sync += counter.eq(counter+1)
				with m.Else():
					m.next = "load_mode_reg_1"
			with m.State("load_mode_reg_1"):
				counter = Signal(8)
				with m.If(counter == 0):
					# cmd
					
					mode = 0b0_00_000_0_111 | cas << 4 | 1<<8
					#print("{:013b}".format(mode))
					m.d.sync += [
						cmd.eq(0b0000),
						ram.addr.eq(mode),
						ram.ba.eq(0)
					]
				
				with m.If(counter < t_mrd):
					m.d.sync += counter.eq(counter+1)
				with m.Else():
					m.d.sync += counter.eq(0)
					m.next = "precharge_2"
			
			with m.State("precharge_2"):
				counter = Signal(4)
				with m.If(counter == 0):
					# cmd
					m.d.sync += [
						cmd.eq(0b0010),
						ram.addr.eq(1<<10)
					]

				with m.If(counter < t_rp):
					m.d.sync += counter.eq(counter+1)
				with m.Else():
					m.next = "auto_refresh_aaa"

			with m.State("auto_refresh_aaa"):
				counter = Signal(4)
				refresh_count = Signal(3)

				with m.If(counter == 0):
					m.d.sync += cmd.eq(0b0001)
				
				with m.If(counter < t_rc):
					m.d.sync += counter.eq(counter+1)
				with m.Else():
					with m.If(refresh_count < 1):
						m.d.sync += [
							refresh_count.eq(refresh_count+1),
							counter.eq(0)
						]
					with m.Else():
						m.next = "load_mode_reg_2"

			with m.State("load_mode_reg_2"):
				counter = Signal(8)
				with m.If(counter == 0):
					# cmd
					
					mode = 0b0_00_000_0_111 | cas << 4
					#print("{:013b}".format(mode))
					m.d.sync += [
						cmd.eq(0b0000),
						ram.addr.eq(mode),
						ram.ba.eq(0)
					]
				
				with m.If(counter < t_mrd):
					m.d.sync += counter.eq(counter+1)
				with m.Else():
					m.d.sync += refresh_timer.eq(0)
					m.d.sync += self.sdram.dqm.eq(0b00)
					m.next = "done"

			with m.State("done"):
				m.d.sync += init_done.eq(1)

		# implement the rest of the owl

		writing = (self.cmd_ack == 1) | (self.cmd_ack == 2)
		reading = (self.cmd_ack == 3)

		banks_active = Signal(2**bank_bits)
		rows_active = Array([ Signal(row_bits) for x in range(0,2**bank_bits) ])

		bank_addr = Signal(bank_bits)
		row_addr = Signal(row_bits)
		col_addr = Signal(col_bits)
		m.d.comb += Cat(col_addr, row_addr, bank_addr).eq(self.addr)

		with m.FSM() as fsm:
			with m.State("init"):
				with m.If(init_done):
					m.next = "idle"

			with m.State("idle"):
				with m.If(refresh_timer > t_refresh):
					m.next = "refresh"
				with m.Else():
					with m.If(self.cmd != 0):
						#m.d.sync += self.cmd_ack.eq(self.cmd)
						m.next = "activate"

					m.d.sync += self.cmd_ack.eq(self.cmd)
			
			with m.State("refresh"):
				counter = Signal(4)
				with m.If(counter == 0):
					m.d.sync += cmd.eq(0b0001)
				with m.If(counter < t_rc-1):
					m.d.sync += counter.eq(counter+1)
				with m.Else():
					m.d.sync += refresh_timer.eq(refresh_timer - t_refresh)
					m.d.sync += counter.eq(0)
					m.next = "idle"

			with m.State("activate"):
				counter = Signal(8)
				with m.If(counter == 0):
					m.d.sync += [
						cmd.eq(0b0011),
						ram.addr.eq(row_addr),
						ram.ba.eq(bank_addr)
					]
				with m.If(counter < t_rcd-1):
					m.d.sync += counter.eq(counter+1)
				with m.Else():
					m.d.sync += counter.eq(0)
					with m.If(reading):
						m.next = "read_cmd"
					with m.Elif(writing):
						# Writes happen IMMEDIATELY after the command.
						m.d.sync += self.wr_valid.eq(1)
						m.d.sync += self.sdram.data_oe.eq(1)
						m.d.sync += self.sdram.data_out.eq(self.data_out)
						m.next = "write_cmd"

			with m.State("read_cmd"):
				counter = Signal(8)
				with m.If(counter == 0):
					m.d.sync += [
						cmd.eq(0b0101),
						ram.addr.eq(col_addr),
						ram.ba.eq(bank_addr)
					]
				with m.If(counter < cas-1):
					m.d.sync += counter.eq(counter+1)
				with m.Else():
					m.d.sync += self.rd_valid.eq(1)
					m.d.sync += counter.eq(0)
					m.next = "read_data"
			
			with m.State("read_data"):
				counter = Signal(8)

				m.d.sync += self.data_in.eq(self.sdram.data_in)

				with m.If(counter == 253):
					m.d.sync += [
						cmd.eq(0b0110), # Burst Terminate
					]
				with m.If(counter == 255):
					m.d.sync += counter.eq(0)
					m.d.sync += self.rd_valid.eq(0)
					m.next = "precharge"
				with m.Else():
					m.d.sync += counter.eq(counter+1)

			with m.State("write_cmd"):
				m.d.sync += [
					cmd.eq(0b0100),
					ram.addr.eq(col_addr),
					ram.ba.eq(bank_addr),

					self.sdram.data_out.eq(self.data_out)
				]
				m.next = "write_data"

			with m.State("write_data"):
				counter = Signal(8)
				m.d.sync += self.sdram.data_out.eq(self.data_out)
				with m.If(counter == 255):
					m.d.sync += [
						cmd.eq(0b0110), # Burst Terminate
					]
					m.d.sync += self.sdram.data_oe.eq(0)
					m.d.sync += self.wr_valid.eq(0)
					m.d.sync += counter.eq(0)
					m.next = "precharge"
				
				m.d.sync += counter.eq(counter+1)

			with m.State("precharge"):
				counter = Signal(8)
				with m.If(counter == 0):
					m.d.sync += [
						cmd.eq(0b0010),
						ram.addr.eq(0),
						ram.ba.eq(bank_addr)
					]

				with m.If(counter < t_rp-1):
					m.d.sync += counter.eq(counter+1)
				with m.Else():
					m.d.sync += counter.eq(0)
					m.next = "idle"
		return m