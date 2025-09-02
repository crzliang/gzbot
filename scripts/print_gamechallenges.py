import asyncio
import os
import asyncpg

POSTGRES_DSN = os.getenv("POSTGRES_DSN")

async def main():
    if not POSTGRES_DSN:
        print("POSTGRES_DSN not set in environment.")
        return
    try:
        conn = await asyncpg.connect(POSTGRES_DSN)
        rows = await conn.fetch("SELECT * FROM \"GameChallenges\" LIMIT 100")
        await conn.close()
        for r in rows:
            print(dict(r))
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    asyncio.run(main())
