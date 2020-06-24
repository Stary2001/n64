import struct

f = open("Super Mario 64 (USA).n64", "rb")
rom_bytes = f.read()
f.close()

rom_words = []

for i in range(0, len(rom_bytes), 2):
    rom_words.append(struct.unpack("H", rom_bytes[i:i+2])[0])

print("{:03x} {:08x} {:04x}".format(0, 0x10000000, rom_words[0]))
print("{:03x} {:08x} {:04x}".format(1, 0x10000002, rom_words[1]))

for addr in range(0x40, 0x1000, 2):
	i = (addr//2 - 0x20) + 2
	print("{:03x} {:08x} {:04x}".format(i, 0x10000000 + addr, rom_words[addr//2]))