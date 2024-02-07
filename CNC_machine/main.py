import fastapi
import fastapi.responses
import signal
import uvicorn
from .CNC_engine import Engine
from .constants import SEVER_APP_ADDR, SEVER_APP_PORT, DRAW_ON_TERMINAL, TIME_MULTIPLIER
import asyncio


async def main():
    eng = Engine(time_mult=TIME_MULTIPLIER, draw=DRAW_ON_TERMINAL)

    app = fastapi.FastAPI(
        title=f"CNC Machine simulator",
        description=__doc__,
        # Don't forget to synchronize with setup.py!
        version="0.1"
    )
    await eng.server_init()

    @app.post("/control/execute_line")
    async def post_execute_line(line: str):
        await eng.execute_gcode_line(line)

    @app.post("/control/execute_file")
    async def post_execute_file(file_path: str):
        await eng.execute_gcode_file(file_path)

    @app.post("/control/pause_gcode")
    async def post_pause_gcode():
        await eng.pause_gcode_execution()

    @app.post("/control/resume_gcode")
    async def post_resume_gcode():
        await eng.resume_gcode_execution()

    @app.post("/control/abort_gcode")
    async def post_abort_gcode():
        await eng.abort_gcode_execution()

    config = uvicorn.Config(app, host=SEVER_APP_ADDR, port=SEVER_APP_PORT)
    server = uvicorn.Server(config)

    def shutdown_engine(a, b):
        eng.close()

    signal.signal(signal.SIGTERM, shutdown_engine)
    signal.signal(signal.SIGINT, shutdown_engine)

    engine_task = asyncio.create_task(eng.run())

    server_task = asyncio.create_task(server.serve())

    await server_task

    await eng.close()

    await engine_task



if __name__ == '__main__':
    asyncio.run(main())
