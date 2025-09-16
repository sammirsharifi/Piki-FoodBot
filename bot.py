import asyncio
import admin_bot
import user_bot

async def run_bots():
    task1 = asyncio.create_task(admin_bot.main())
    task2 = asyncio.create_task(user_bot.main())

    await asyncio.gather(task1, task2)

if __name__ == "__main__":
    asyncio.run(run_bots())
