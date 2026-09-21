"""One-off DB connectivity smoke test."""
import asyncio
from fedretina.db.postgres import init_pool, close_pool, get_pool


async def main() -> None:
    await init_pool()
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT COUNT(*) AS n FROM public.audit_logs")
        print("audit_logs count:", rows[0]["n"])

        seq = await conn.fetchval("SELECT last_value FROM public.audit_log_chain_seq")
        print("chain_seq last_value:", seq)

        version = await conn.fetchval("SELECT version()")
        print("postgres version:", version.split(",")[0])
    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
