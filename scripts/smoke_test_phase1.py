import asyncio
import os
import sys

# Ensure the context_server package can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../context_server')))

from app.obsidian_backend import backend


async def main():
    print("Running Phase 1 Smoke Test...")
    print("Testing Obsidian backend health...")
    is_healthy = await backend.health()
    print(f"Health: {'OK' if is_healthy else 'Degraded'}")

    if not is_healthy:
        print("Backend not healthy, skipping search.")
        sys.exit(1)

    print("Testing search_simple for 'hello'...")
    try:
        results = await backend.search_simple("hello")
        if results:
            print("Found hits:")
            for hit in results[:1]: # Print just the first hit
                print(hit)
        else:
            print("No hits found, but the connection was successful.")
    except Exception as e:
        print(f"Failed to query: {e}")
        sys.exit(1)
    finally:
        await backend.aclose()

if __name__ == "__main__":
    asyncio.run(main())
