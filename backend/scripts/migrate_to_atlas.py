"""Migrasi data PT SJM Sawit dari MongoDB Emergent (preview) ke MongoDB Atlas.

Pakai:
    cd /app/backend
    SOURCE_MONGO_URL="$MONGO_URL" SOURCE_DB="test_database" \
    TARGET_MONGO_URL="mongodb+srv://user:pass@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority" \
    TARGET_DB="ptsjm_sawit" \
    python scripts/migrate_to_atlas.py

Mode default = MERGE (upsert per dokumen, data lama di Atlas tidak dihapus).
Tambahkan WIPE_TARGET=1 kalau ingin isi collection di Atlas dikosongkan dulu.
"""
import asyncio
import os
import sys

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

COLLECTIONS = ['users', 'owners', 'batches', 'transactions', 'finance_days', 'prices', 'settings']
KEYS = {
    'users': 'email',
    'owners': 'id',
    'batches': 'id',
    'transactions': 'id',
    'prices': 'date',
    'settings': 'key',
}


async def main():
    src_url = os.environ.get('SOURCE_MONGO_URL') or os.environ.get('MONGO_URL')
    src_db = os.environ.get('SOURCE_DB') or os.environ.get('DB_NAME')
    tgt_url = os.environ.get('TARGET_MONGO_URL')
    tgt_db = os.environ.get('TARGET_DB') or 'ptsjm_sawit'
    if not src_url or not src_db:
        sys.exit('SOURCE_MONGO_URL / SOURCE_DB (atau MONGO_URL / DB_NAME) wajib diisi.')
    if not tgt_url:
        sys.exit('TARGET_MONGO_URL (connection string MongoDB Atlas) wajib diisi.')

    src = AsyncIOMotorClient(src_url)[src_db]
    tgt = AsyncIOMotorClient(tgt_url)[tgt_db]
    wipe = os.environ.get('WIPE_TARGET') == '1'

    print(f'Sumber : {src_db}')
    print(f'Tujuan : {tgt_db} (wipe={wipe})\n')
    total = 0
    for name in COLLECTIONS:
        docs = await src[name].find({}, {'_id': 0}).to_list(100000)
        if wipe:
            await tgt[name].delete_many({})
        if not docs:
            print(f'  {name:<14} 0 dokumen (dilewati)')
            continue
        key = KEYS.get(name)
        if key:
            for d in docs:
                if key in d:
                    await tgt[name].update_one({key: d[key]}, {'$set': d}, upsert=True)
                else:
                    await tgt[name].insert_one(d)
        else:
            for d in docs:
                q = {'batch_id': d.get('batch_id'), 'date': d.get('date')}
                await tgt[name].update_one(q, {'$set': d}, upsert=True)
        total += len(docs)
        print(f'  {name:<14} {len(docs)} dokumen dipindahkan')

    await tgt.users.create_index('email', unique=True)
    print(f'\nSelesai. Total {total} dokumen. Index unik email dibuat di Atlas.')


if __name__ == '__main__':
    asyncio.run(main())
