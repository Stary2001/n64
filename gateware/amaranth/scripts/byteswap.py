import struct

f = open("Super Mario 64 (USA).n64", "rb")
rom_bytes = f.read()
f.close()

rom_words = []

for i in range(0, len(rom_bytes), 2):
    rom_words.append(struct.unpack("H", rom_bytes[i:i+2])[0])

f = open("sm64_swapped.n64","wb")

for i in range(0, len(rom_words)):
    f.write(struct.pack(">H", rom_words[i]))
