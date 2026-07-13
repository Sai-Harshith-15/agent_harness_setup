"""Delta indexing: watch the repo and re-graphify changed files only.
Run as a background task from main.py's lifespan, or standalone: python -m app.indexing.watcher
"""
import asyncio

from watchfiles import awatch

from .graphify import ROOT, graphify


async def watch_and_index() -> None:
    graphify()  # initial full pass (delta-aware, so cheap on restart)
    try:
        async for _changes in awatch(
            ROOT,
            watch_filter=lambda _c, p: not any(
                skip in p for skip in ('.git', 'node_modules', '__pycache__', '.next', 'hooks', '.pytest_cache', '.ruff_cache', '.venv')
            ),
        ):
            stats = graphify()  # only changed hashes get re-indexed
            print(f"[delta-index] {stats}")
    except asyncio.CancelledError:
        pass  # clean shutdown — let the caller await us


if __name__ == "__main__":
    asyncio.run(watch_and_index())
