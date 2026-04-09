# PRD - Persona Creation GUI (Vibe Coding)

## 1. Product Overview
Persona Creation GUI adalah aplikasi berbasis AI untuk membantu tim Product, Design, dan Marketing membuat persona secara cepat, terstruktur, dan mudah dibagikan. Produk ini memadukan prompt generation dengan "vibe controls" agar output persona tetap kreatif namun relevan untuk pengambilan keputusan.

## 2. Latar Belakang dan Masalah
Saat ini pembuatan persona sering dilakukan manual di dokumen/slides dengan kualitas yang bervariasi antar individu dan tim. Dampaknya:
- proses pembuatan lambat,
- format dan kedalaman persona tidak konsisten,
- output sulit langsung dipakai untuk prioritisasi produk.

Kondisi ini menurunkan kecepatan alignment lintas fungsi dan meningkatkan risiko keputusan berbasis asumsi yang lemah.

## 3. Tujuan MVP
1. Mempercepat waktu pembuatan persona pertama.
2. Menstandarkan struktur persona agar konsisten lintas project.
3. Menyediakan kontrol gaya (vibe) tanpa mengorbankan kualitas isi.
4. Memudahkan distribusi persona melalui ekspor PDF/PNG/JSON.

## 4. Non-Goals MVP
- Real-time collaboration multi-editor.
- Integrasi penuh dengan seluruh tools riset pihak ketiga.
- Model evaluasi statistik lanjutan untuk validitas persona.
- Otomasi penuh tanpa proses review manusia.

## 5. Persona dan Pengguna Utama
### Primary Persona: UX Designer / UX Researcher
- Membutuhkan persona cepat untuk workshop, ideasi, dan arahan desain.
- Perlu output yang mudah di-edit berdasarkan insight lapangan.

### Secondary Persona: Product Manager / Founder
- Membutuhkan ringkasan user profile yang bisa dipakai untuk prioritas fitur.
- Perlu format konsisten untuk komunikasi stakeholder.

### Tertiary Persona: Marketing / Content Strategist
- Membutuhkan framing persona untuk segmentasi pesan dan channel.

## 6. User Stories Prioritas
1. Sebagai UX Designer, saya ingin generate persona dari prompt singkat agar bisa memulai workshop lebih cepat.
2. Sebagai PM, saya ingin menyesuaikan field persona agar sesuai konteks bisnis agar keputusan fitur lebih tepat.
3. Sebagai marketer, saya ingin mengekspor persona ke PDF agar mudah dibagikan ke tim.
4. Sebagai user baru, saya ingin template siap pakai agar tidak bingung memulai dari nol.

## 7. Ruang Lingkup Fitur MVP
### 7.1 Persona Generation
- Input prompt bebas + context opsional (industri, segmen, market).
- Sistem menghasilkan draft persona dengan struktur standar.

### 7.2 Vibe Controls
- Slider/toggle:
  - Formal <-> Casual
  - Rational <-> Emotional
  - Minimalist <-> Expressive
- Pilihan archetype (Explorer, Achiever, Caregiver, dll).

### 7.3 Persona Card & Inline Editing
- Field inti:
  - identity summary,
  - goals,
  - pain points,
  - motivations,
  - behavior patterns,
  - preferred channels/tools,
  - representative quote.
- Semua field dapat diedit langsung (inline).
- Indikator "AI-generated" vs "user-edited".

### 7.4 Template System
- Template domain awal: SaaS, e-commerce, fintech, edukasi, B2B services.
- Template memengaruhi starter prompt dan struktur default.

### 7.5 Save, Version, Export
- Simpan persona per project.
- Export format: PDF, PNG, JSON.
- Versi awal menyimpan metadata perubahan dasar.

### 7.6 Basic Quality Check
- Warning jika field terlalu singkat/generik.
- Reminder potensi bias agar user melakukan review kritis.

## 8. User Flow MVP
1. User masuk ke dashboard dan memilih "Create Persona".
2. User memilih template (opsional).
3. User mengisi prompt dan context.
4. User mengatur vibe controls.
5. User menjalankan generate.
6. Sistem menampilkan persona draft.
7. User mengedit field / regenerate parsial.
8. User menyimpan persona ke project.
9. User mengekspor persona ke PDF/PNG/JSON.

## 9. Functional Requirements
### FR-01 Generate Persona
- Sistem menerima prompt + context.
- Sistem menghasilkan draft persona dengan field minimum.

### FR-02 Vibe Customization
- User dapat mengubah tone/style/archetype sebelum atau sesudah generate.
- User dapat regenerate parsial per bagian.

### FR-03 Persona Editing
- User dapat mengedit semua field.
- Sistem menandai field yang diubah user.

### FR-04 Template Selection
- User dapat memilih template domain saat awal pembuatan.

### FR-05 Save and Load
- User dapat menyimpan dan membuka ulang persona.

### FR-06 Export
- User dapat export ke PDF/PNG/JSON dengan layout konsisten.

### FR-07 Quality Feedback
- Sistem memberi warning kualitas teks saat relevan.

## 10. Non-Functional Requirements
- Performance: waktu generate target p95 <= 8 detik.
- Reliability: error rate request valid < 2%.
- Security: data terenkripsi in transit.
- Accessibility: keyboard navigable dan kontras memadai.
- Localization: dukungan ID/EN untuk UI inti.

## 11. Data Model (MVP)
### Entity: Persona
- id, project_id, name, demographic_summary, context, quote
- goals[], pain_points[], motivations[], behaviors[], channels_tools[]
- vibe_profile (tone, style, archetype)
- created_by, created_at, updated_at, version

### Entity: Project
- id, name, description, owner_id, created_at

### Entity: Template
- id, name, industry, default_fields, starter_prompts[]

## 12. Success Metrics
### Product Metrics
- Time to First Persona (median) <= 5 menit.
- Persona Completion Rate >= 70%.
- Export/Share Rate >= 40%.

### Adoption/Quality Metrics
- >= 60% draft mendapat edit lanjutan user.
- CSAT internal >= 4.2/5 dalam fase pilot.

## 13. Asumsi dan Risiko
### Asumsi
- Tim menerima AI output sebagai draft awal, bukan final mutlak.
- User memiliki konteks bisnis minimal untuk memberi prompt yang relevan.

### Risiko
- Persona terlalu generik jika input minim.
- Potensi bias dalam output model.
- Adopsi rendah jika flow terasa kompleks.

### Mitigasi
- Wajibkan context minimum pada prompt.
- Tampilkan quality hints dan bias reminder.
- Sediakan template + onboarding singkat.

## 14. Roadmap Singkat
### Phase 1 (MVP, 2-4 minggu)
- Generate, edit, save, export PDF/PNG/JSON.

### Phase 2 (4-8 minggu)
- Template expansion, quality hint yang lebih cerdas, mode compare.

### Phase 3 (8-12 minggu)
- Version history lebih lengkap dan kolaborasi ringan.

## 15. Delivery Checklist
- PRD disetujui Product + Design lead.
- Scope MVP dan non-goals dikunci.
- KPI baseline ditetapkan sebelum pilot.
- Definisi quality rubric persona disepakati lintas tim.
