"""QA cleanup: remove test-created transactions, TEST_QA owners and test batches; restore BATCH-2026-09 active."""
import asyncio, os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path('/app/backend/.env'))
from motor.motor_asyncio import AsyncIOMotorClient

SEED_OWNERS = {'Ita Sari', 'Epit', 'Sita Rosiani', 'Suparmin'}


async def main():
    db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
    r = await db.transactions.delete_many({})
    print('transactions deleted:', r.deleted_count)
    r = await db.owners.delete_many({'name': {'$nin': list(SEED_OWNERS)}})
    print('test owners deleted:', r.deleted_count)
    r = await db.batches.delete_many({'id': {'$ne': 'BATCH-2026-09'}})
    print('test batches deleted:', r.deleted_count)
    await db.batches.update_one({'id': 'BATCH-2026-09'}, {'$set': {'active': True}, '$unset': {'archived_at': ''}})
    r = await db.users.delete_many({'email': {'$regex': '^test_qa'}})
    print('test users deleted:', r.deleted_count)
    r = await db.counters.delete_many({})
    print('tx counters reset:', r.deleted_count)
    r = await db.login_attempts.delete_many({})
    print('login attempts cleared:', r.deleted_count)
    print('owners:', [o['name'] for o in await db.owners.find({}, {'_id': 0}).to_list(50)])
    print('batches:', [(b['id'], b.get('active')) for b in await db.batches.find({}, {'_id': 0}).to_list(50)])
    print('users:', [u['email'] for u in await db.users.find({}, {'_id': 0}).to_list(50)])
    print('tx count:', await db.transactions.count_documents({}))

asyncio.run(main())
