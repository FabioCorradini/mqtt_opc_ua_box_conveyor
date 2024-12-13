import asyncio
from .pool_boiler_engine import Engine, PotUI


async def main():
    engine = Engine(PotUI())
    await engine.run()


if __name__ == '__main__':
    asyncio.run(main())
