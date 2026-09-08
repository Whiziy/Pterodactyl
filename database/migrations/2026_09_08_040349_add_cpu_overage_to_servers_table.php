<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('servers', function (Blueprint $table) {
            $table->timestamp('cpu_overage_since')->nullable()->after('reminded_h1');
            $table->boolean('cpu_auto_stopped')->default(false)->after('cpu_overage_since');
        });
    }

    public function down(): void
    {
        Schema::table('servers', function (Blueprint $table) {
            $table->dropColumn(['cpu_overage_since', 'cpu_auto_stopped']);
        });
    }
};
