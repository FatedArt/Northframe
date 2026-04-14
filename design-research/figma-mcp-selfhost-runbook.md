# NorthFrame Figma MCP Self-Host Runbook

Dokumen ini adalah panduan setup **Figma Console MCP self-host** untuk workflow NorthFrame, ditulis agar bisa langsung dieksekusi oleh AI agent atau engineer.

## Tujuan

- Menyediakan dua opsi setup: **Local-Only Hardened** dan **Cloud Self-Host**.
- Menghubungkan Cursor ke Figma MCP dengan konfigurasi aman.
- Menjaga secret tetap aman (tanpa hardcode token di repo).

## Arsitektur Singkat

### Local-Only Hardened

- Cursor menjalankan `figma-console-mcp` via `npx` (local runtime).
- Figma Desktop Bridge terhubung via WebSocket lokal.
- Auth: PAT via env var (`FIGMA_ACCESS_TOKEN`) untuk call ke API Figma.

### Cloud Self-Host (Opsional)

- MCP server: `https://figma-console-mcp.<subdomain>.workers.dev/mcp`
- Cursor: `~/.cursor/mcp.json` (server `figma-console-selfhosted`)
- Figma Desktop Bridge plugin (Cloud Mode) terhubung via pairing code.
- Auth: Bearer PAT (`FIGMA_ACCESS_TOKEN`) untuk endpoint `/mcp`.

## Prasyarat

- Node.js 18+ (disarankan 20+)
- Akun Cloudflare + `workers.dev` subdomain aktif (hanya untuk profil Cloud Self-Host)
- Figma Personal Access Token (PAT) aktif
- Figma Desktop ter-install
- Cursor ter-install

## Profil Setup (Pilih Salah Satu)

### A) Local-Only Hardened (Direkomendasikan)

Gunakan ini jika prioritas utama adalah minim exposure ke layanan eksternal.

- Cursor menjalankan MCP lokal via NPX.
- Tidak menggunakan endpoint `workers.dev` untuk Figma MCP.
- Desktop Bridge tetap berjalan lokal.

Contoh `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "figma-console-selfhosted": {
      "command": "npx",
      "args": ["-y", "figma-console-mcp@1.22.3"],
      "env": {
        "FIGMA_ACCESS_TOKEN": "${env:FIGMA_ACCESS_TOKEN}",
        "ENABLE_MCP_APPS": "true"
      }
    }
  }
}
```

Set env PAT (jangan hardcode token di JSON):

```bash
echo 'export FIGMA_ACCESS_TOKEN="figd_xxx_replace_me"' >> ~/.zshrc
source ~/.zshrc
```

Jika sebelumnya pernah deploy relay Cloudflare dan ingin hard-disable:

```bash
cd ~/Research/cursor-figma/cursor/Research/figma-console-mcp
npx wrangler delete figma-console-mcp --force
curl -s -o /dev/null -w "%{http_code}" https://figma-console-mcp.northframe.workers.dev/health
```

Expected verifikasi: `404`.

#### Quick Start (Laptop Pribadi)

1. Set `~/.cursor/mcp.json` pakai `npx -y figma-console-mcp@1.22.3` + `${env:FIGMA_ACCESS_TOKEN}`.
2. Set PAT di shell profile (`~/.zshrc`), lalu `source ~/.zshrc`.
3. Restart Cursor total.
4. Buka Figma Desktop Bridge plugin dan jalankan `Check Figma status`.
5. (Opsional hard-disable) hapus worker Cloudflare dengan `wrangler delete` seperti di atas.

### B) Cloud Self-Host di Cloudflare (Opsional)

Gunakan ini jika membutuhkan cloud relay/pairing lintas web AI client.

> Catatan: Langkah `1) ... 9)` di bawah ini adalah alur **Profil B (Cloud Self-Host)**.

## 1) Clone dan Setup Project MCP

```bash
cd ~/Research/cursor-figma/cursor/Research
git clone https://github.com/southleft/figma-console-mcp.git
cd figma-console-mcp
npm install
```

## 2) Login Cloudflare dan Set Secret

```bash
npx wrangler login
npx wrangler whoami
npx wrangler secret put FIGMA_ACCESS_TOKEN
```

## 3) Konfigurasi Wrangler (Akun + KV)

Pastikan `wrangler.jsonc` menggunakan `account_id` akun aktif (`wrangler whoami`).

Buat KV namespace jika belum ada:

```bash
npx wrangler kv namespace create OAUTH_TOKENS
npx wrangler kv namespace create OAUTH_STATE
```

Update ID KV hasil command di `wrangler.jsonc` pada `kv_namespaces`.

## 4) Build dan Deploy

```bash
npm run cf-typegen
npm run build:cloudflare
npm run deploy
```

Validasi:

```bash
curl "https://figma-console-mcp.<subdomain>.workers.dev/health"
```

Expected: `status = healthy`.

## 5) Konfigurasi Cursor MCP (Self-host)

Edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "figma-console-selfhosted": {
      "url": "https://figma-console-mcp.<subdomain>.workers.dev/mcp",
      "headers": {
        "Authorization": "Bearer ${env:FIGMA_ACCESS_TOKEN}"
      }
    }
  }
}
```

> Penting: gunakan format `${env:...}` untuk interpolasi env di Cursor.

## 6) Set Environment Variable Lokal (untuk Cursor)

Tambahkan ke `~/.zshrc`:

```bash
export FIGMA_ACCESS_TOKEN='figd_xxx_replace_me'
```

Lalu:

```bash
source ~/.zshrc
```

Quit total Cursor dan buka lagi.

## 7) Patch Plugin Bridge untuk Domain Self-host

Secara default plugin Cloud Mode mengarah ke domain publik Southleft. Untuk self-host, update:

- `~/.figma-console-mcp/plugin/manifest.json`
- `~/.figma-console-mcp/plugin/ui.html`
- `~/.figma-console-mcp/plugin/ui-full.html`

### 7a) Manifest allowed domains

Pastikan domain berikut ada di `allowedDomains` dan `devAllowedDomains`:

- `wss://figma-console-mcp.<subdomain>.workers.dev`
- `https://figma-console-mcp.<subdomain>.workers.dev`

### 7b) Cloud relay host

Di `ui.html` dan `ui-full.html`, set:

```js
var CLOUD_RELAY_HOST = 'wss://figma-console-mcp.<subdomain>.workers.dev';
```

### 7c) Re-import plugin

Di Figma Desktop:

- Plugins -> Development -> Import plugin from manifest...
- Pilih `~/.figma-console-mcp/plugin/manifest.json`

## 8) Pairing Cloud Mode

1. Dari MCP client, panggil tool `figma_pair_plugin` untuk generate pairing code.
2. Masukkan code di plugin Cloud Mode (tanpa spasi).
3. Klik `Connect`.
4. Status harus `Connected to cloud relay`.

## 9) Validasi End-to-End

### HTTP-level

```bash
curl -i \
  -H "Authorization: Bearer $FIGMA_ACCESS_TOKEN" \
  -H "Accept: text/event-stream" \
  "https://figma-console-mcp.<subdomain>.workers.dev/mcp"
```

Expected: `HTTP 200` + `content-type: text/event-stream`.

### MCP tool-level

- Jalankan `figma_get_file_data` tanpa `fileUrl` saat plugin aktif.
- Expected: return metadata file Figma aktif (bukan error unauthorized/no file URL).

## Rotasi Token (Revoke & Rotate PAT)

1. Revoke token lama di Figma PAT settings.
2. Buat token baru (scope minimum).
3. Update secret Cloudflare:

```bash
npx wrangler secret put FIGMA_ACCESS_TOKEN
npm run deploy
```

4. Update env lokal:

```bash
export FIGMA_ACCESS_TOKEN='figd_new_token'
source ~/.zshrc
```

5. Restart Cursor.

## Troubleshooting Cepat

### Error: `OAuth not configured on server`
- Biasanya request masuk flow OAuth karena header Bearer tidak terbaca.
- Cek `mcp.json` harus `${env:FIGMA_ACCESS_TOKEN}`.
- Restart total Cursor setelah set env.

### Pairing selalu `Disconnected`
- Cek `CLOUD_RELAY_HOST` di `ui.html`/`ui-full.html` masih ke Southleft atau tidak.
- Cek `manifest.json` sudah allow domain self-host.
- Re-import plugin setelah patch.

### Error deploy: `workers.dev subdomain required`
- Aktifkan subdomain account-level di Cloudflare Workers & Pages.

### Error deploy: `KV namespace not found`
- Buat KV baru di akun sendiri lalu update `wrangler.jsonc`.

## Catatan Keamanan

- Jangan hardcode token di repo.
- Hindari share screenshot yang menampilkan token.
- Revoke token yang pernah terekspos.
- Gunakan scope minimum.

