# Pterodactyl Panel (Whizy Custom Fork)

Fork custom dari [Pterodactyl Panel](https://github.com/pterodactyl/panel) dengan tambahan fitur **auto-expire server**, dipakai buat integrasi sama bot penjualan hosting Whizy Store.

## Fitur Tambahan (Custom)

Fork ini menambahkan sistem masa aktif (`expires_at`) per server di atas Pterodactyl standar:

### 1. Kolom `expires_at` pada tabel `servers`
Migration baru: `database/migrations/2026_08_09_193038_add_expires_at_to_servers_table.php`
Menyimpan timestamp kapan sebuah server kedaluwarsa. Nullable secara default di level kolom, tapi di level aplikasi **selalu diisi otomatis** (lihat poin 2 & 3).

### 2. Auto-expire saat create server
Endpoint: `POST /api/application/servers`

Field baru (opsional): `expires_in_days` (integer)

- Kalau diisi (misal `expires_in_days: 60`) → server dibuat dengan `expires_at = now() + 60 hari`.
- Kalau **tidak diisi / kosong** → default otomatis **30 hari**.
- Kalau diisi **0 atau negatif** → request **ditolak** (`DisplayException`). Tidak ada konsep server unlimited di sistem ini.

File yang terlibat:
- `app/Http/Requests/Api/Application/Servers/StoreServerRequest.php`
- `app/Services/Servers/ServerCreationService.php`

### 3. Perpanjang masa aktif (extend) via update details
Endpoint: `PATCH /api/application/servers/{id}/details`

Field baru (opsional): `extend_days` (integer)

- Base perhitungan: kalau `expires_at` server saat ini masih di masa depan, tanggal itu jadi basis (`expires_at + extend_days`). Kalau sudah lewat/kosong, basisnya `now()`.
- Sama seperti create: kosong → default 30 hari, 0/negatif → ditolak.
- Field lain (`external_id`, `name`, `user`, `description`) tetap wajib dikirim persis sesuai `UpdateServerDetailsRequest::validated()` — Laravel FormRequest men-strip field yang tidak didefinisikan di `validated()`, jadi payload harus lengkap.

File yang terlibat:
- `app/Http/Requests/Api/Application/Servers/UpdateServerDetailsRequest.php`
- `app/Services/Servers/DetailsModificationService.php`

### 4. `expires_at` di response API
Ditambahkan ke `ServerTransformer.php` supaya field ini ikut muncul di response `GET /api/application/servers/{id}` (format ISO timestamp via `formatTimestamp()`, `null` kalau belum pernah diset).

File yang terlibat:
- `app/Transformers/Api/Application/ServerTransformer.php`

## Contoh Pemakaian API

**Buat server baru, expired 45 hari dari sekarang:**

```bash
curl -X POST "https://panel.example.com/api/application/servers" \
  -H "Authorization: Bearer ptla_xxxxx" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "name": "server-baru",
    "user": 1,
    "egg": 15,
    "docker_image": "...",
    "startup": "...",
    "environment": {},
    "limits": {"memory": 512, "swap": 0, "disk": 1024, "io": 500, "cpu": 100},
    "feature_limits": {"databases": 0, "allocations": 0, "backups": 0},
    "allocation": {"default": 1},
    "expires_in_days": 45
  }'
```

**Perpanjang server 30 hari (default, tanpa isi extend_days):**

```bash
curl -X PATCH "https://panel.example.com/api/application/servers/1/details" \
  -H "Authorization: Bearer ptla_xxxxx" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "external_id": null,
    "name": "server-baru",
    "user": 1,
    "description": ""
  }'
```

**Cek sisa masa aktif server:**

```bash
curl -X GET "https://panel.example.com/api/application/servers/1" \
  -H "Authorization: Bearer ptla_xxxxx" \
  -H "Accept: application/json"
```

## Tutorial Pemakaian

### A. Install dari Nol (server baru, belum ada Pterodactyl sama sekali)

1. Ikuti instalasi resmi Pterodactyl sampai selesai (webserver, database, PHP, Redis, dll) — ikuti setiap langkah persis seperti panduan resmi:
   https://pterodactyl.io/panel/1.0/getting_started.html

2. Bedanya cuma di langkah "clone repository" — ganti dengan clone fork ini:
   ```bash
   cd /var/www
   git clone https://github.com/Whiziy/Pterodactyl.git pterodactyl
   cd pterodactyl
   ```

3. Lanjutkan sisa langkah instalasi resmi seperti biasa:
   ```bash
   composer install --no-dev --optimize-autoloader
   cp .env.example .env
   php artisan key:generate --force
   php artisan p:environment:setup
   php artisan p:environment:database
   php artisan migrate --seed
   ```
   Migration kolom `expires_at` otomatis ikut jalan pas `php artisan migrate --seed` karena sudah ada di folder `database/migrations/`.

4. Buat user admin pertama:
   ```bash
   php artisan p:user:make
   ```

5. Set permission & webserver (nginx/apache) sesuai panduan resmi, lalu buka panel di browser. Selesai — semua server yang dibuat lewat panel ini otomatis punya `expires_at`.

### B. Sudah Punya Panel Pterodactyl Berjalan (mau nambahin fitur ini ke panel existing)

1. **Backup dulu** database & seluruh folder panel — ini wajib, karena kita akan menimpa beberapa file inti.
   ```bash
   cd /var/www/pterodactyl
   php artisan down
   tar -czf ~/pterodactyl-backup-$(date +%Y%m%d).tar.gz .
   ```

2. Tambahkan fork ini sebagai remote tambahan, lalu tarik perubahannya:
   ```bash
   git remote add whizy https://github.com/Whiziy/Pterodactyl.git
   git fetch whizy
   git merge whizy/main
   ```
   Kalau muncul conflict (karena kamu punya modifikasi lain di panel), selesaikan manual — file yang paling mungkin bentrok cuma 5 file yang disebut di section "Fitur Tambahan" di atas. Kalau nggak yakin, pakai `git diff` buat lihat detail perubahannya sebelum di-resolve.

3. Jalankan migration buat nambah kolom `expires_at` ke tabel `servers`:
   ```bash
   php artisan migrate
   ```

4. Clear semua cache biar perubahan kepakai:
   ```bash
   php artisan config:clear
   php artisan cache:clear
   php artisan view:clear
   composer dump-autoload
   php artisan up
   ```

5. **Test dulu sebelum dipakai produksi** — buat 1 server percobaan lewat API tanpa isi `expires_in_days`, lalu cek `expires_at` otomatis keisi 30 hari:
   ```bash
   php artisan tinker --execute="echo \Pterodactyl\Models\Server::latest()->first()->expires_at;"
   ```
   Kalau muncul tanggal ~30 hari dari sekarang, fitur sudah aktif dengan benar.

### C. Cara Pakai Sehari-hari (via API)

Semua request butuh header berikut:
```
Authorization: Bearer ptla_xxxxxxxxxxxxxxxxxxxx
Content-Type: application/json
Accept: application/json
```
`ptla_...` adalah **Application API Key**, dibuat lewat menu **Admin → Application API** di panel (bukan Client API / `ptlc_...`, karena endpoint di bawah ini semuanya level admin).

| Aksi | Method & Endpoint | Field penting |
|---|---|---|
| Buat server baru | `POST /api/application/servers` | `expires_in_days` (opsional, default 30 hari kalau kosong) |
| Perpanjang server | `PATCH /api/application/servers/{id}/details` | `extend_days` (opsional, default 30 hari) — field `name`, `user`, `description`, `external_id` wajib ikut dikirim |
| Cek sisa masa aktif | `GET /api/application/servers/{id}` | Lihat `attributes.expires_at` |
| Lihat semua server | `GET /api/application/servers` | Bisa dipakai buat scan server yang mau expired (loop & cek `expires_at`) |

**Penting — aturan wajib:**
- `extend_days` dan `expires_in_days` **tidak pernah boleh diisi `0` atau angka negatif** — request akan otomatis ditolak dengan error `DisplayException`, karena tidak ada konsep server unlimited di fork ini.
- Kalau dikosongkan (tidak dikirim sama sekali), otomatis dianggap **30 hari**.
- Untuk endpoint `PATCH .../details`, field selain `extend_days` (`external_id`, `name`, `user`, `description`) **wajib dikirim semua**, walau nilainya tidak berubah — kalau tidak, Laravel akan menganggap field itu kosong dan menimpa data lama.

### D. Troubleshooting Umum

| Masalah | Kemungkinan Penyebab | Solusi |
|---|---|---|
| `expires_at` tetap `null` setelah create/extend | `expires_in_days`/`extend_days` tidak lolos validasi karena field lain di payload tidak lengkap | Cek semua field wajib sudah dikirim, cek response error-nya |
| Error `DisplayException: ... tidak boleh 0` | Kamu mengirim `extend_days: 0` atau `expires_in_days: 0` | Hapus field itu dari payload (biar default 30) atau isi angka > 0 |
| `updated_at` server tidak berubah setelah PATCH | Payload field-nya sama persis dengan data lama (Eloquent tidak menganggap ada perubahan) | Pastikan `extend_days` terkirim dan bernilai valid |
| Response API tidak ada field `expires_at` | Belum patch `ServerTransformer.php`, atau file lama masih dipakai (cache) | `php artisan config:clear && php artisan cache:clear` |

## Catatan

- Backup file asli sebelum patch tersimpan otomatis dengan ekstensi `.bak`, `.bak2`, `.bak3` di masing-masing file yang diubah — aman dihapus setelah dipastikan semuanya berjalan normal.
- Tidak ada fitur "unlimited" masa aktif secara desain — semua server harus punya `expires_at`.
- Fork ini tidak mengubah struktur inti Pterodactyl, jadi update dari upstream (`pterodactyl/panel`) tetap bisa di-merge selama tidak menyentuh 5 file yang disebutkan di atas.
