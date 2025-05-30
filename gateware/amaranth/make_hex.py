import sys

if len(sys.argv) <= 2:
    print("Usage: {sys.argv[0]} [input] [output]")
    sys.exit(1)

with open(sys.argv[1], "rb") as flash_bin:
    with open(sys.argv[2], "w") as hex_text:
        flash_bytes = flash_bin.read()
        hex_text.write(' '.join(map(lambda b: f'{b:02x}', flash_bytes)))
        