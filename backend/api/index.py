"""Vercel Python serverless entrypoint (OPSIONAL).

Hanya dipakai kalau Anda benar-benar ingin backend FastAPI jalan di Vercel.
Catatan penting (baca DEPLOY.md): serverless punya cold start, timeout 10s (plan Hobby),
dan koneksi MongoDB dibuat ulang tiap invocation -> untuk aplikasi timbangan ini
Railway / Render (server biasa) lebih stabil dan tetap gratis.

Struktur yang dibaca Vercel:
  backend/vercel.json  -> routing semua request ke file ini
  backend/api/index.py -> file ini, meng-import FastAPI app dari server.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app  # noqa: E402  (FastAPI ASGI app)

# Vercel Python runtime mencari variabel bernama `app` (ASGI) — sudah tersedia dari import di atas.
