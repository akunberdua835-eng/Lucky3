# PRD — Sistem Rekap Penerimaan Sawit PT SJM

## Problem statement
PT SJM membutuhkan sistem rekap penerimaan dan pembelian buah sawit dari petani kecil yang realistis, tervalidasi, mudah diedit, dapat dicetak sebagai voucher jembatan timbang, dan siap dipakai finance.

## Architecture decisions
- React workspace (single-file App.js) + FastAPI + MongoDB.
- JWT bearer (secret di backend/.env) + bcrypt + approval admin untuk signup + brute-force lockout (5 gagal → 423, 15 menit, per ip:email, $inc atomik).
- Kredensial admin di backend/.env (ADMIN_EMAIL/ADMIN_PASSWORD), hash di-resync saat startup bila berubah.
- Netto Kg = Gross - Tare (tare kosong = 0); Ton 2 desimal; Total = Netto × harga.
- Kode transaksi SJM-YYYYMM-XXX: nomor = max urutan yang ada (per batch per bulan) + 1 → jika semua transaksi dihapus, penomoran mulai lagi dari 001 (permintaan user 2026-09-01).
- Batch bulanan dikelola penuh: buat untuk bulan mana pun (label Indonesia, mis. "Agustus 2026", duplikat bulan → "· Periode 2"), aktifkan batch mana pun, hapus batch beserta transaksinya (admin-only; jika batch aktif dihapus, batch terbaru diaktifkan otomatis).
- Generator ATOMIC: seluruh kandidat dibuat di memori → validasi → insert_many sekaligus; infeasible → 422 (target/maximum/shortage/reason/status) tanpa menulis apa pun. Aturan: 07:00–16:00, skip 12:00–13:00 (dipakai otomatis jika target tak terkejar, dicatat di note), arrival berikut > exit sebelumnya, exit 20–40 mnt, pemilik tak berurutan, pemilik sama berjeda ≥105 mnt, gross ≤ kapasitas, target EXACT.
- Excel export via openpyxl dengan RUMUS editable (=G-H, ROUND, total =SUM), header hijau, freeze panes.
- Resend notification hook non-blocking (asyncio.to_thread); tanpa RESEND_API_KEY pengiriman **MOCKED** ke log.
- CORS eksplisit dari CORS_ORIGINS di .env.

## Personas
- Admin utama: approve/reject akun, kelola & hapus batch, semua fitur operator.
- Operator timbang: catat/koreksi penerimaan, generator, voucher, kelola pemilik & batch (tanpa hapus batch).
- Finance: filter harian/bulanan/per-pemilik + export Excel berumus.

## Core requirements (semua terpenuhi)
- Login, signup pending, approval + reject admin.
- Master pemilik/kendaraan (seed: Ita Sari Pick Up 1300, Epit Tossa 600, Sita Rosiani Hilux 1800, Suparmin Hilux 1800) + tambah/edit via UI.
- CRUD transaksi (tambah/edit dengan kode tetap/hapus satu/hapus per tanggal dibatasi batch), validasi jam & kapasitas.
- Generator natural exact-target lintas tanggal.
- Rekap + grafik + filter tanggal + Excel berumus.
- Voucher printable (kode, periode, jam, gross/tare/netto, harga, total, tanda tangan).

## Implemented
- 2026-02-21: MVP auth, batch, owners, transaksi, generator, analytics, excel, voucher.
- 2026-09-01 (fork): generator atomic + aturan jadwal penuh; delete-by-date + UI; edit transaksi (kode tetap); CRUD pemilik UI; reject akun; Excel formula openpyxl; export via axios blob (fix 401); brute-force lockout; JWT_SECRET/ADMIN_* ke .env + resync hash; CORS eksplisit; toaster bottom-right; catch + empty states; modal Escape/backdrop close; kode transaksi reset setelah hapus (max+1 per batch+bulan); kelola batch penuh (buat bulan tertentu/aktifkan/hapus, label Indonesia). Testing: iteration_1 (25/27→fix), iteration_2 (34/34 backend, 100% frontend); fitur batch/kode-reset diverifikasi curl + screenshot.

## Prioritized backlog
- P0: Konfigurasi RESEND_API_KEY produksi + verifikasi domain pengirim (email masih MOCKED).
- P1: Voucher field editable sebelum cetak; date picker lokal dd/mm/yyyy (shadcn calendar) menggantikan input native.
- P2: DELETE endpoint pemilik; kartu progres target per periode parsial; bundel PDF voucher; sesi httpOnly cookie; throttle per-IP.

## Catatan teknis
- Test suite: /app/backend/tests (jalankan pytest -n 0; setelahnya python tests/qa_cleanup.py dari /app/backend).
- data-testid penting: manage-batch-button, create-batch-button, new-batch-month-input, activate-batch-{id}, delete-batch-{id}, delete-day-date-input, delete-day-button, edit-{id}, voucher-{id}, approve-user-{id}, reject-user-{id}, add-owner-button, export-excel-button, open-generator-button, run-generator-button.
