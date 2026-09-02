import asyncio, os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path('/app/backend/.env'))
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
    for u in await db.users.find({}, {'_id': 0}).to_list(50):
        print(u['email'], u['role'], u['status'], 'hash_prefix=', str(u.get('password_hash'))[:7])
    print('batches:', [(b['id'], b.get('active')) for b in await db.batches.find({}, {'_id': 0}).to_list(50)])
    print('owners:', [(o['name'], o['capacity_kg']) for o in await db.owners.find({}, {'_id': 0}).to_list(50)])
    print('tx count:', await db.transactions.count_documents({}))
    codes = [t['transaction_code'] for t in await db.transactions.find({}, {'_id': 0, 'transaction_code': 1}).to_list(5000)]
    print('dup codes:', len(codes) - len(set(codes)))

asyncio.run(main())
