#!/usr/bin/env python3
import subprocess
from datetime import datetime

BASE = "/var/www/pterodactyl/"

def write_new(path, content, label):
    full = BASE + path
    try:
        with open(full, "x", encoding="utf-8") as f:
            f.write(content)
        print(f"OK [buat baru] {label}")
    except FileExistsError:
        print(f"SKIP [{label}]: file sudah ada, tidak ditimpa.")

def patch(path, old, new, marker, label):
    full = BASE + path
    with open(full, "r", encoding="utf-8") as f:
        content = f.read()
    if marker in content:
        print(f"SKIP [{label}]: sudah pernah dipatch.")
        return
    if old not in content:
        print(f"GAGAL [{label}]: pattern lama tidak ditemukan.")
        return
    with open(full + ".bak_expcheck", "w", encoding="utf-8") as f:
        f.write(content)
    content = content.replace(old, new, 1)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"OK [{label}]: berhasil dipatch. Backup: {full}.bak_expcheck")

# ── 1. Migration: kolom reminder flag ───────────────────────
ts = datetime.now().strftime("%Y_%m_%d_%H%M%S")
migration_name = f"database/migrations/{ts}_add_reminder_flags_to_servers_table.php"
write_new(migration_name, """<?php

use Illuminate\\Database\\Migrations\\Migration;
use Illuminate\\Database\\Schema\\Blueprint;
use Illuminate\\Support\\Facades\\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('servers', function (Blueprint $table) {
            $table->boolean('reminded_h3')->default(false)->after('expires_at');
            $table->boolean('reminded_h1')->default(false)->after('reminded_h3');
        });
    }

    public function down(): void
    {
        Schema::table('servers', function (Blueprint $table) {
            $table->dropColumn(['reminded_h3', 'reminded_h1']);
        });
    }
};
""", "migration reminder flags")

# ── 2. Artisan Command: cek expired + kirim reminder ────────
write_new("app/Console/Commands/CheckExpiredServers.php", """<?php

namespace Pterodactyl\\Console\\Commands;

use Carbon\\Carbon;
use Illuminate\\Console\\Command;
use Illuminate\\Support\\Facades\\Http;
use Illuminate\\Support\\Facades\\Log;
use Pterodactyl\\Models\\Server;
use Pterodactyl\\Services\\Servers\\ServerDeletionService;

class CheckExpiredServers extends Command
{
    protected $signature = 'whizy:check-expired-servers';
    protected $description = 'Cek server expired: kirim reminder H-3/H-1 via Telegram, hapus server yang sudah lewat expired.';

    public function handle(ServerDeletionService $deletionService): int
    {
        $token = env('TELEGRAM_BOT_TOKEN');
        if (empty($token)) {
            $this->warn('TELEGRAM_BOT_TOKEN belum diset di .env — reminder TIDAK akan terkirim (auto-delete tetap jalan).');
        }

        $now = Carbon::now();
        $servers = Server::query()->whereNotNull('expires_at')->get();

        $deleted = 0;
        $remindedH3 = 0;
        $remindedH1 = 0;

        foreach ($servers as $server) {
            $expiresAt = $server->expires_at;
            if (!$expiresAt) {
                continue;
            }

            if ($expiresAt->lte($now)) {
                try {
                    if ($token && $server->external_id) {
                        $this->sendTelegram($token, $server->external_id,
                            "\xf0\x9f\x97\x91\xef\xb8\x8f Server *{$server->name}* sudah DIHAPUS karena tidak diperpanjang sebelum masa aktifnya habis."
                        );
                    }
                    $deletionService->handle($server);
                    $this->info("Deleted server #{$server->id} ({$server->name}) — expired {$expiresAt}");
                    $deleted++;
                } catch (\\Throwable $e) {
                    Log::error("Gagal hapus server expired #{$server->id}: " . $e->getMessage());
                    $this->error("Gagal hapus server #{$server->id}: " . $e->getMessage());
                }
                continue;
            }

            $daysLeft = (int) $now->diffInDays($expiresAt, false);

            if ($daysLeft <= 3 && $daysLeft > 1 && !$server->reminded_h3) {
                if ($token && $server->external_id) {
                    $this->sendTelegram($token, $server->external_id,
                        "\xe2\x9a\xa0\xef\xb8\x8f Server *{$server->name}* akan expired dalam ~3 hari ({$expiresAt->format('d M Y H:i')}). Perpanjang sekarang lewat bot supaya tidak terhapus otomatis."
                    );
                }
                $server->update(['reminded_h3' => true]);
                $remindedH3++;
            }

            if ($daysLeft <= 1 && !$server->reminded_h1) {
                if ($token && $server->external_id) {
                    $this->sendTelegram($token, $server->external_id,
                        "\xf0\x9f\x9a\xa8 Server *{$server->name}* akan expired dalam ~1 hari ({$expiresAt->format('d M Y H:i')}). Segera perpanjang, kalau tidak server akan DIHAPUS OTOMATIS."
                    );
                }
                $server->update(['reminded_h1' => true]);
                $remindedH1++;
            }
        }

        $this->info("Selesai. Dihapus: {$deleted}, Reminder H-3: {$remindedH3}, Reminder H-1: {$remindedH1}");
        return self::SUCCESS;
    }

    private function sendTelegram(string $token, string $chatId, string $text): void
    {
        try {
            Http::timeout(10)->post("https://api.telegram.org/bot{$token}/sendMessage", [
                'chat_id' => $chatId,
                'text' => $text,
                'parse_mode' => 'Markdown',
            ]);
        } catch (\\Throwable $e) {
            Log::warning("Gagal kirim reminder Telegram ke {$chatId}: " . $e->getMessage());
        }
    }
}
""", "Artisan command CheckExpiredServers")

# ── 3. Daftarin ke scheduler (Kernel.php) ───────────────────
patch(
    "app/Console/Kernel.php",
    "        $schedule->command('cache:prune-stale-tags')->hourly();",
    "        $schedule->command('cache:prune-stale-tags')->hourly();\n"
    "        $schedule->command('whizy:check-expired-servers')->hourly();",
    "whizy:check-expired-servers",
    "Kernel.php scheduler registration"
)

# ── 4. Reset reminded_h3/h1 tiap kali server diperpanjang ───
patch(
    "app/Services/Servers/DetailsModificationService.php",
    "            'expires_at' => $expiresAt,\n            ])->saveOrFail();",
    "            'expires_at' => $expiresAt,\n"
    "                'reminded_h3' => false,\n"
    "                'reminded_h1' => false,\n"
    "            ])->saveOrFail();",
    "'reminded_h3' => false",
    "DetailsModificationService reset reminder flags"
)

print("\n=== Jalankan migration & cek command terdaftar ===")
r1 = subprocess.run(["php", "artisan", "migrate", "--force"], cwd=BASE, capture_output=True, text=True)
print(r1.stdout, r1.stderr)

r2 = subprocess.run(["php", "artisan", "schedule:list"], cwd=BASE, capture_output=True, text=True)
print(r2.stdout, r2.stderr)
