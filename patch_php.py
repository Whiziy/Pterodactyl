#!/usr/bin/env python3
# Jalankan ini LANGSUNG DI SERVER whizy (bukan di HP), lewat SSH.

PATH = "/var/www/pterodactyl/app/Http/Requests/Api/Application/Servers/UpdateServerDetailsRequest.php"

OLD = "            'description' => $this->input('description'),"
NEW = OLD + "\n            'extend_days' => $this->input('extend_days'),"

with open(PATH, "r", encoding="utf-8") as f:
    content = f.read()

if "extend_days" in content:
    print("SKIP: 'extend_days' sudah ada di file, tidak ada perubahan.")
elif OLD not in content:
    print("GAGAL: baris yang dicari tidak ditemukan persis seperti ini:")
    print(repr(OLD))
    print("\nIsi baris yang mengandung 'description' saat ini:")
    for i, line in enumerate(content.splitlines(), 1):
        if "description" in line:
            print(f"  baris {i}: {line!r}")
else:
    with open(PATH + ".bak", "w", encoding="utf-8") as f:
        f.write(content)
    new_content = content.replace(OLD, NEW, 1)
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("OK: 'extend_days' berhasil ditambahkan.")
    print(f"Backup asli disimpan di: {PATH}.bak")

print("\n--- Cek hasil ---")
import subprocess
result = subprocess.run(["php", "-l", PATH], capture_output=True, text=True)
print(result.stdout.strip())
print(result.stderr.strip())

with open(PATH, "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if "extend_days" in line:
            print(f"baris {i}: {line.rstrip()}")
