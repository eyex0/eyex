import asyncio
import logging

from app.core.logging import setup_logging

logger = logging.getLogger(__name__)


async def main():
    setup_logging()
    logger.info("EyeX LangGraph worker started")
    try:
        while True:
            await asyncio.sleep(10)
    except KeyboardInterrupt:
        logger.info("Worker shutting down")


if __name__ == "__main__":
    asyncio.run(main())
