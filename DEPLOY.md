# Panduan Deploy PT SJM Sawit — Vercel + Railway/Render + MongoDB Atlas (Gratis)

Target: **tanpa biaya deploy Emergent (50 kredit)**. Aplikasi tetap bisa terus dikembangkan di Emergent,
lalu tinggal `Save to GitHub` → Vercel & Railway otomatis re-deploy.

> **Ringkasan rekomendasi**
> | Bagian | Hosting | Biaya |
> |---|---|---|
> | Frontend React | **Vercel** | Gratis (Hobby) |
> | Backend FastAPI | **Railway** atau **Render** | Gratis |
> | Database | **MongoDB Atlas M0** | Gratis 512 MB |
>
> Backend FastAPI **sebaiknya JANGAN di Vercel**: Vercel serverless punya cold start,
> batas eksekusi 10 detik (Hobby), dan koneksi Mongo dibuat ulang setiap request.
> Fitur berat aplikasi ini (generator transaksi, export Excel multi-sheet, streaming file)
> bisa timeout. Kalau tetap ingin coba, file `backend/vercel.json` + `backend/api/index.py`
> sudah disiapkan (lihat Lampiran B).

---

## 1. Siapkan MongoDB Atlas (M0 gratis)

1. Daftar di https://cloud.mongodb.com → **Create a project** (mis. `PT SJM`).
2. **Create Cluster** → pilih **M0 Free** → region terdekat (mis. Singapore `ap-southeast-1`) → Create.
3. **Database Access** → *Add New Database User*:
   - Authentication: Password
   - Username: `ptsjm_app`, Password: buat yang kuat (**hindari karakter `@ : / ?`** agar URL aman)
   - Role: `Atlas admin` (atau `readWriteAnyDatabase`)
4. **Network Access** → *Add IP Address* → **0.0.0.0/0** (Allow access from anywhere).
   Wajib, karena IP Railway/Render/Vercel berubah-ubah.
5. **Connect** → *Drivers* → Python → copy connection string, lalu ganti `<password>`:
   ```
   mongodb+srv://ptsjm_app:PASSWORD@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0
   ```
   Simpan sebagai nilai `MONGO_URL`. Nama database diisi lewat `DB_NAME` (mis. `ptsjm_sawit`).

---

## 2. Push kode ke GitHub

Di Emergent: tombol **Save to GitHub** (repo `Lucky2`). Pastikan file berikut sudah ada di repo
(sudah dibuat otomatis): `frontend/vercel.json`, `backend/Dockerfile`, `backend/Procfile`,
`render.yaml`, `railway.json`, `backend/.env.example`, `frontend/.env.example`.

> `.env` asli **tidak** ikut ter-commit (memang begitu). Semua nilai rahasia diisi di dashboard
> Railway/Render/Vercel.

---

## 3. Deploy Backend FastAPI

### Opsi A — Railway (paling mudah)
1. https://railway.app → **New Project** → *Deploy from GitHub repo* → pilih `Lucky2`.
2. Settings → **Root Directory**: `backend` (kalau Railway tidak otomatis membaca `railway.json`).
3. Tab **Variables** → isi:
   | Variable | Nilai |
   |---|---|
   | `MONGO_URL` | connection string Atlas dari langkah 1 |
   | `DB_NAME` | `ptsjm_sawit` |
   | `JWT_SECRET` | string acak 64 karakter |
   | `ADMIN_EMAIL` | `yumaclovstar@gmail.com` |
   | `ADMIN_PASSWORD` | `178910` (ganti kalau mau) |
   | `BACKUP_ADMIN_EMAILS` | `admin@ptsjm.co.id` |
   | `CORS_ORIGINS` | `https://nama-app-anda.vercel.app` (isi setelah langkah 4, boleh diupdate) |
   | `RESEND_API_KEY` | opsional |
4. Settings → **Networking** → *Generate Domain* → dapat URL, mis. `https://ptsjm-backend.up.railway.app`.
5. Tes: buka `https://ptsjm-backend.up.railway.app/api/` → harus balas JSON status.

### Opsi B — Render
1. https://render.com → **New** → **Blueprint** → pilih repo (otomatis membaca `render.yaml`).
2. Isi env var yang bertanda `sync: false` (`MONGO_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `CORS_ORIGINS`, dst).
3. Deploy → dapat URL `https://ptsjm-backend.onrender.com`.
   > Catatan: free plan Render "tidur" setelah 15 menit idle → request pertama bisa lambat ~30 detik.

---

## 4. Deploy Frontend di Vercel

1. https://vercel.com → **Add New Project** → import repo `Lucky2`.
2. **Root Directory**: `frontend`  → Framework otomatis terdeteksi *Create React App*
   (`frontend/vercel.json` sudah mengatur build & SPA rewrite).
3. **Environment Variables** (Production + Preview):
   | Variable | Nilai |
   |---|---|
   | `REACT_APP_BACKEND_URL` | `https://ptsjm-backend.up.railway.app` (tanpa `/` di akhir, tanpa `/api`) |
   | `CI` | `false` |
4. **Deploy** → dapat URL `https://nama-app-anda.vercel.app`.
5. **Kembali ke Railway/Render** → update `CORS_ORIGINS` = URL Vercel tadi → restart service.
   (Boleh beberapa domain, dipisah koma, termasuk domain custom Anda.)

---

## 5. Login pertama & pindahkan data

- Backend otomatis membuat: admin utama (`ADMIN_EMAIL`/`ADMIN_PASSWORD`), 1 batch bulan berjalan,
  dan 4 master pemilik (Ita Sari, Epit, Sita Rosiani, Suparmin). Jadi Atlas kosong pun langsung bisa dipakai.
- Mau memindahkan data yang sudah ada di preview Emergent ke Atlas:
  ```bash
  cd /app/backend
  TARGET_MONGO_URL="mongodb+srv://ptsjm_app:PASSWORD@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority" \
  TARGET_DB="ptsjm_sawit" \
  python scripts/migrate_to_atlas.py
  ```
  Script memindahkan `users, owners, batches, transactions, finance_days, prices, settings`
  secara upsert (aman diulang). Tambahkan `WIPE_TARGET=1` bila ingin mengosongkan Atlas dulu.

---

## 6. Checklist setelah live

- [ ] `https://BACKEND/api/` balas JSON → backend sehat
- [ ] Login admin berhasil di domain Vercel (kalau gagal & console error CORS → `CORS_ORIGINS` salah)
- [ ] Catat 1 transaksi → muncul di Ringkasan
- [ ] Export Excel (lengkap / per pemilik / harian / laba rugi / harga) terunduh
- [ ] Grading harian + edit PPh 22 tersimpan
- [ ] Atlas → Collections: data benar-benar masuk ke `ptsjm_sawit`

---

## Lampiran A — Semua environment variable

**Backend** (`backend/.env.example`): `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `ADMIN_EMAIL`,
`ADMIN_PASSWORD`, `BACKUP_ADMIN_EMAILS`, `CORS_ORIGINS`, `RESEND_API_KEY` (opsional).

**Frontend** (`frontend/.env.example`): `REACT_APP_BACKEND_URL`, `CI=false`.

> Di Emergent, `MONGO_URL` dan `REACT_APP_BACKEND_URL` dikelola platform — **jangan diubah** di sini.
> Nilai Atlas/Railway hanya diisi di dashboard hosting masing-masing.

## Lampiran B — Kalau tetap ingin backend di Vercel

File sudah disiapkan: `backend/vercel.json` + `backend/api/index.py`.
Langkah: buat project Vercel kedua → Root Directory `backend` → isi env var backend seperti tabel di atas.

Risiko yang harus Anda terima:
- Cold start ~1–3 detik pada request pertama.
- Timeout 10 detik (Hobby): **generator target besar** dan **export Excel lengkap** berpotensi gagal.
- Koneksi Mongo dibuat ulang tiap invocation → boros koneksi Atlas M0 (limit 500).
- Notifikasi email & job panjang tidak cocok di serverless.

Kalau nanti terasa lambat/timeout, pindahkan backend ke Railway/Render — cukup ganti
`REACT_APP_BACKEND_URL` di Vercel, tanpa ubah kode.
