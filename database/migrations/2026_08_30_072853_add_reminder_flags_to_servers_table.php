<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

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
