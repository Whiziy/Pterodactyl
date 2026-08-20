#!/usr/bin/env python3
PATH = "/var/www/pterodactyl/app/Transformers/Api/Application/ServerTransformer.php"

OLD = "            'description' => $server->description,"
NEW = OLD + "\n            'expires_at' => $server->expires_at ? $this->formatTimestamp($server->expires_at) : null,"

with open(PATH, "r", encoding="utf-8") as f:
    content = f.read()

if "'expires_at'" in content:
    print("SKIP: 'expires_at' sudah ada di file, tidak ada perubahan.")
elif OLD not in content:
    print("GAGAL: baris yang dicari tidak ditemukan persis.")
else:
    with open(PATH + ".bak", "w", encoding="utf-8") as f:
        f.write(content)
    new_content = content.replace(OLD, NEW, 1)
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("OK: 'expires_at' berhasil ditambahkan ke transformer.")
    print(f"Backup asli disimpan di: {PATH}.bak")

print("\n--- Cek hasil ---")
import subprocess
result = subprocess.run(["php", "-l", PATH], capture_output=True, text=True)
print(result.stdout.strip())
print(result.stderr.strip())

with open(PATH, "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if "expires_at" in line:
            print(f"baris {i}: {line.rstrip()}")
