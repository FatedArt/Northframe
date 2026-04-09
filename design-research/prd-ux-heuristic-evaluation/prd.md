# PRD - UX Heuristic Evaluation App (MVP)

## 1. Ringkasan Produk
UX Heuristic Evaluation App adalah web app internal untuk membantu tim Product dan Design melakukan evaluasi usability secara konsisten berbasis 10 Nielsen Heuristics. Produk ini menggantikan workflow manual (spreadsheet + slide + chat) dengan alur terstruktur dari pembuatan evaluasi, scoring, pencatatan evidence, sampai ekspor laporan.

## 2. Latar Belakang dan Masalah
Tim internal saat ini melakukan heuristic review dengan format yang berbeda-beda, sehingga:
- kualitas temuan tidak konsisten antar evaluator,
- scoring sulit dibandingkan antar produk atau antar waktu,
- insight tersebar di banyak dokumen dan sulit ditindaklanjuti.

Kondisi ini memperlambat prioritisasi perbaikan UX dan meningkatkan risiko rekomendasi yang tidak berbasis bukti yang sama kuat.

## 3. Tujuan MVP
1. Menstandarkan proses heuristic evaluation end-to-end.
2. Mempercepat waktu pembuatan laporan evaluasi.
3. Menyediakan baseline score usability yang dapat dibandingkan antar evaluasi.
4. Memudahkan tracking issue UX dari temuan ke status tindak lanjut.

## 4. Non-Goals MVP
- Integrasi langsung dengan analytics tools (Mixpanel, GA, Amplitude).
- Integrasi otomatis dengan Jira/Linear.
- AI-generated recommendations otomatis.
- Mobile native app (iOS/Android).
- Collaboration real-time multi-editor (Google Docs style).

## 5. Persona dan Pengguna Utama
### Primary Persona: UX/Product Designer Internal
- Menjalankan evaluasi rutin untuk fitur baru/existing.
- Membutuhkan framework konsisten dan output laporan cepat.

### Secondary Persona: Product Manager
- Membaca hasil evaluasi untuk prioritisasi backlog.
- Membutuhkan ringkasan severity dan rekomendasi aksi.

## 6. Use Cases Prioritas
1. Evaluator membuat sesi evaluasi baru untuk sebuah produk/fitur.
2. Evaluator menambahkan temuan per heuristic lengkap dengan evidence.
3. Evaluator memberi severity dan confidence per temuan.
4. Tim melihat dashboard skor keseluruhan dan distribusi masalah.
5. Evaluator mengekspor laporan ringkas untuk dibagikan ke stakeholder.

## 7. Ruang Lingkup Fitur MVP
### 7.1 Project & Evaluation Management
- Buat project evaluasi (nama produk, platform, evaluator, tanggal).
- Buat sesi evaluasi dalam project.
- Status sesi: Draft, In Review, Final.

### 7.2 Heuristic Checklist
- Daftar 10 Nielsen Heuristics sebagai struktur utama input.
- Untuk tiap heuristic, evaluator dapat menambahkan banyak temuan.
- Template field temuan:
  - Judul temuan
  - Deskripsi masalah
  - Lokasi (halaman/screen/flow)
  - Evidence (teks + URL/screenshot reference)
  - Severity (0-4)
  - Confidence (Low/Medium/High)
  - Rekomendasi perbaikan singkat

### 7.3 Scoring & Summary
- Hitung score per heuristic berbasis severity.
- Tampilkan:
  - total findings,
  - rata-rata severity,
  - top heuristics dengan masalah terbanyak,
  - tren sederhana per sesi (jika ada sesi sebelumnya).

### 7.4 Reporting
- Export laporan ke Markdown dan PDF-ready layout.
- Ringkasan berisi:
  - executive summary,
  - top issues by severity,
  - daftar rekomendasi quick wins.

### 7.5 Basic Tracking
- Status temuan: Open, In Progress, Resolved, Won't Fix.
- Filter berdasarkan heuristic, severity, dan status.

## 8. User Flow MVP
1. User login.
2. User membuat project.
3. User membuat evaluation session.
4. User mengisi temuan per heuristic.
5. User review summary score.
6. User finalize session.
7. User export report dan share ke stakeholder.

## 9. Functional Requirements
### FR-01 Authentication
- User internal dapat login/logout dengan email perusahaan (minimal magic link atau SSO-compatible stub untuk MVP).

### FR-02 Create & Manage Evaluation
- User dapat membuat, mengedit, mengarsipkan project dan sesi evaluasi.

### FR-03 Findings CRUD
- User dapat membuat, melihat, mengubah, dan menghapus temuan.

### FR-04 Heuristic Mapping
- Setiap temuan wajib terhubung ke satu heuristic.

### FR-05 Severity & Confidence
- Setiap temuan wajib memiliki severity; confidence opsional tetapi disarankan.

### FR-06 Dashboard Summary
- Sistem menampilkan ringkasan skor otomatis saat data berubah.

### FR-07 Export Report
- User dapat mengekspor laporan per sesi.

### FR-08 Search & Filter
- User dapat mencari temuan dan memfilter berdasarkan atribut inti.

### FR-09 Audit Trail (basic)
- Simpan metadata `created_by`, `updated_by`, `created_at`, `updated_at`.

## 10. Non-Functional Requirements
- Web-only, desktop-first responsive.
- Performa: waktu load halaman dashboard < 2 detik untuk <= 500 temuan/sesi.
- Keandalan: autosave draft setiap 20 detik.
- Keamanan: data hanya bisa diakses user terautentikasi.
- Kegunaan: form input temuan dapat diselesaikan tanpa training formal.

## 11. Data Model (MVP)
### Entity: User
- id, name, email, role, created_at

### Entity: Project
- id, name, product_area, owner_id, created_at, archived_at

### Entity: EvaluationSession
- id, project_id, title, platform, status, evaluator_ids, created_at, finalized_at

### Entity: Finding
- id, session_id, heuristic_id, title, description, location, evidence_text, evidence_url, severity, confidence, recommendation, status, created_by, updated_by, created_at, updated_at

### Entity: Heuristic
- id, code, name, description

## 12. Success Metrics
### Product Metrics
- 80% evaluasi internal menggunakan app ini dalam 2 bulan pertama.
- Waktu pembuatan laporan turun minimal 40% dibanding baseline manual.
- >= 70% temuan severity tinggi memiliki status tindak lanjut dalam 30 hari.

### Usability Metrics
- SUS internal score >= 75 setelah 1 bulan pilot.
- Completion rate pembuatan sesi evaluasi end-to-end >= 90%.

## 13. Asumsi dan Risiko
### Asumsi
- Tim sudah familiar dengan Nielsen Heuristics.
- Data evaluasi tidak memerlukan compliance enterprise khusus pada MVP.

### Risiko
- Variasi cara menilai severity antar evaluator dapat menurunkan konsistensi score.
- Adopsi rendah jika form dianggap terlalu panjang.
- Export tidak sesuai format stakeholder dapat kembali ke workflow lama.

### Mitigasi
- Berikan severity rubric terstandar di UI.
- Sediakan template temuan dan preset rekomendasi singkat.
- Lakukan pilot ke 1-2 squad dulu sebelum rollout penuh.

## 14. Roadmap Singkat
### Phase 1 (MVP, 4-6 minggu)
- Core CRUD evaluasi, scoring, dashboard, export, tracking status.

### Phase 2 (Post-MVP)
- Integrasi Jira/Linear, kolaborasi reviewer, komentar, mention.

### Phase 3
- AI-assisted clustering temuan dan rekomendasi perbaikan.

## 15. Delivery Checklist
- PRD disetujui Product + Design lead.
- Scope MVP terkunci (fitur non-goals tidak ikut sprint awal).
- Definisi severity rubric disepakati lintas evaluator.
- Instrumentasi event analytics dasar disiapkan untuk ukur adopsi.
