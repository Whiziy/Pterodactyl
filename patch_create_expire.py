#!/usr/bin/env python3
import subprocess

BASE = "/var/www/pterodactyl/"

def patch(path, old, new, marker):
    full = BASE + path
    with open(full, "r", encoding="utf-8") as f:
        content = f.read()
    if marker in content:
        print(f"SKIP [{path}]: sudah pernah dipatch.")
        return
    if old not in content:
        print(f"GAGAL [{path}]: pattern lama tidak ditemukan.")
        return
    with open(full + ".bak3", "w", encoding="utf-8") as f:
        f.write(content)
    content = content.replace(old, new, 1)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"OK [{path}]: berhasil dipatch. Backup: {full}.bak3")
    result = subprocess.run(["php", "-l", full], capture_output=True, text=True)
    print(result.stdout.strip())
    print(result.stderr.strip())

# ── 1. StoreServerRequest.php: rules() ──────────────────────
patch(
    "app/Http/Requests/Api/Application/Servers/StoreServerRequest.php",
    "            'start_on_completion' => 'sometimes|boolean',\n        ];",
    "            'start_on_completion' => 'sometimes|boolean',\n"
    "            'expires_in_days' => 'sometimes|nullable|integer|min:1',\n        ];",
    "expires_in_days"
)

# ── 2. StoreServerRequest.php: validated() ──────────────────
patch(
    "app/Http/Requests/Api/Application/Servers/StoreServerRequest.php",
    "            'oom_disabled' => array_get($data, 'oom_disabled'),\n        ];",
    "            'oom_disabled' => array_get($data, 'oom_disabled'),\n"
    "            'expires_in_days' => array_get($data, 'expires_in_days'),\n        ];",
    "'expires_in_days' => array_get"
)

# ── 3. ServerCreationService.php: default 30 hari + tolak 0 ─
patch(
    "app/Services/Servers/ServerCreationService.php",
    "        if (!empty($data['expires_in_days'])) {\n"
    "            $data['expires_at'] = now()->addDays((int) $data['expires_in_days']);\n"
    "        }",
    "        $rawExpiresInDays = Arr::get($data, 'expires_in_days');\n"
    "        if ($rawExpiresInDays === null || $rawExpiresInDays === '') {\n"
    "            $expiresInDays = 30;\n"
    "        } else {\n"
    "            $expiresInDays = (int) $rawExpiresInDays;\n"
    "            if ($expiresInDays <= 0) {\n"
    "                throw new \\Pterodactyl\\Exceptions\\DisplayException(\n"
    "                    'expires_in_days tidak boleh 0 atau negatif — tidak ada paket unlimited di sini.'\n"
    "                );\n"
    "            }\n"
    "        }\n"
    "        $data['expires_at'] = now()->addDays($expiresInDays);",
    "tidak ada paket unlimited"
)

print("\n=== Selesai. Cek ringkasan di atas: pastikan semua OK, bukan GAGAL. ===")
