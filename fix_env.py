#!/usr/bin/env python3
import re

PATH = "/var/www/pterodactyl/.env"

with open(PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Pisahkan baris yang nyambung (mis. "SESSION_SECURE_COOKIE=trueTELEGRAM_BOT_TOKEN=...")
def split_merged(match):
    prefix = match.group(1)
    token_line = "TELEGRAM_BOT_TOKEN=" + match.group(2)
    return prefix + "\n" + token_line

content = re.sub(r"([^\n]+?)TELEGRAM_BOT_TOKEN=([^\n]*)", split_merged, content)

# 2. Hilangkan duplikat baris TELEGRAM_BOT_TOKEN=..., simpan cuma yang pertama
lines = content.split("\n")
seen_token = False
result = []
for line in lines:
    if line.startswith("TELEGRAM_BOT_TOKEN="):
        if seen_token:
            continue  # skip duplikat
        seen_token = True
    result.append(line)

with open(PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(result))

print("OK: .env sudah dibersihkan.")
print("\n--- Isi baris terkait sekarang ---")
for line in result:
    if "SESSION_SECURE_COOKIE" in line or "TELEGRAM_BOT_TOKEN" in line:
        print(line)
