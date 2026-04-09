# Design System Health Dashboard

Dashboard lokal untuk audit kualitas design system dari file Figma.

## Setup

```bash
cd design-audit/design-system-audit
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Buka http://localhost:5555 di browser.

## Cara Pakai

1. Paste link Figma file di input field
2. Masukkan [Personal Access Token](https://www.figma.com/developers/api#access-tokens) dari Figma
3. Klik **Audit** untuk menjalankan pengecekan
4. Klik **Export Documentation** untuk menyimpan hasil audit ke folder **`Research/[Frame:Component]/`** di **root monorepo northframe** (bukan di dalam `design-audit/`)

## Figma Personal Access Token

Buat token di: Figma → Settings → Personal access tokens → Generate new token.

## Struktur export

Relatif ke root **northframe/**:

```
Research/
  [Frame Folder:Nama Component]/
    desktop.md
    mobile.md
```
