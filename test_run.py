import asyncio
import os
from main import run_once, setup_logging

if __name__ == '__main__':
    # Run in single mode to execute just once
    os.environ["RUN_MODE"] = "single"
    logger = setup_logging()
    asyncio.run(run_once(logger=logger))
