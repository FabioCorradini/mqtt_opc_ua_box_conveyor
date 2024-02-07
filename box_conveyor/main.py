from .box_conveyor import Engine
import asyncio


async def main():
    eng = Engine()

    await eng.server_init()

    try:
        await eng.run()
    except KeyboardInterrupt:
        print("")
        # eng.mqtt_client.loop_stop()
        print("Closing")


if __name__ == '__main__':
    asyncio.run(main())
