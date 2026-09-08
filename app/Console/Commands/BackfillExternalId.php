<?php

namespace Pterodactyl\Console\Commands;

use Illuminate\Console\Command;
use Pterodactyl\Models\Server;
use Pterodactyl\Repositories\Wings\DaemonFileRepository;

class BackfillExternalId extends Command
{
    protected $signature = 'whizy:backfill-external-id {server_identifier} {--path=user_panels.json}';
    protected $description = 'Ambil user_panels.json langsung dari server bot via Wings, lalu isi external_id server lama (format unik telegram_id:server_id), TANPA memicu perpanjangan expires_at.';

    public function handle(DaemonFileRepository $fileRepository): int
    {
        $identifier = $this->argument('server_identifier');
        $path = $this->option('path');

        $server = Server::query()
            ->where('uuid', $identifier)
            ->orWhere('uuidShort', $identifier)
            ->first();

        if (!$server) {
            $this->error("Server dengan identifier '{$identifier}' tidak ditemukan.");
            return self::FAILURE;
        }

        try {
            $content = $fileRepository->setServer($server)->getContent($path);
        } catch (\Throwable $e) {
            $this->error("Gagal ambil file '{$path}' dari server: " . $e->getMessage());
            return self::FAILURE;
        }

        $data = json_decode($content, true);
        if (!is_array($data)) {
            $this->error('Isi file bukan JSON yang valid.');
            return self::FAILURE;
        }

        $updated = 0;
        $skipped = 0;
        $notFound = 0;
        $failed = 0;

        foreach ($data as $telegramUserId => $panelList) {
            if (!is_array($panelList)) {
                continue;
            }
            foreach ($panelList as $panel) {
                $serverId = $panel['server_id'] ?? null;
                if (!$serverId) {
                    continue;
                }

                $target = Server::find($serverId);
                if (!$target) {
                    $this->warn("Server ID {$serverId} tidak ditemukan di database, dilewati.");
                    $notFound++;
                    continue;
                }

                if (!empty($target->external_id)) {
                    $skipped++;
                    continue;
                }

                try {
                    $target->external_id = $telegramUserId . ':' . $serverId;
                    $target->save();
                    $this->info("Server #{$serverId} ({$target->name}) -> external_id={$target->external_id}");
                    $updated++;
                } catch (\Throwable $e) {
                    $this->error("Gagal simpan server #{$serverId}: " . $e->getMessage());
                    $failed++;
                }
            }
        }

        $this->info("Selesai. Update: {$updated}, Skip (sudah ada): {$skipped}, Tidak ditemukan: {$notFound}, Gagal: {$failed}");
        return self::SUCCESS;
    }
}
