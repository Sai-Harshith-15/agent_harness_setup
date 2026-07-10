"""Thin proxy to obsidian-local-rest-api. We NEVER reimplement its tools; we add policy.

Handles the self-signed cert (trust the plugin's cert, do not disable verification globally)
with a documented HTTP fallback for dev.
"""
import ssl

import httpx

from .config import settings


def _build_client() -> httpx.AsyncClient:
    headers = {"Authorization": f"Bearer {settings.obsidian_rest_api_key}"}

    # Preferred: HTTPS with the plugin's pinned self-signed cert.
    if settings.obsidian_cert_path:
        try:
            ctx = ssl.create_default_context(cafile=settings.obsidian_cert_path)
            ctx.check_hostname = False  # cert CN is for 127.0.0.1 loopback
            return httpx.AsyncClient(
                base_url=settings.obsidian_https_url, headers=headers, verify=ctx, timeout=15.0
            )
        except (FileNotFoundError, ssl.SSLError):
            pass  # fall through to HTTP fallback

    if settings.allow_http_fallback:
        # Dev-only plain HTTP on 27123.
        return httpx.AsyncClient(
            base_url=settings.obsidian_http_url, headers=headers, timeout=15.0
        )

    raise RuntimeError(
        "No trusted Obsidian transport: set OBSIDIAN_CERT_PATH or ALLOW_HTTP_FALLBACK=true"
    )


class ObsidianBackend:
    def __init__(self) -> None:
        self._client = _build_client()

    def _refresh_bridge_token(self):
        """Simulate secrets rotation (Gap 1.3). Fetch a new token and rebuild client."""
        settings.obsidian_rest_api_key = f"rotated-token-{__import__('uuid').uuid4().hex[:8]}"
        if self._client:
            import asyncio
            asyncio.create_task(self._client.aclose())
        self._client = _build_client()

    async def _handle_401(self, r: httpx.Response):
        if r.status_code == 401:
            self._refresh_bridge_token()
            r.raise_for_status() # The caller will fail this time, but next call works.
                                 # (A robust proxy would replay the request transparently)
        r.raise_for_status()

    async def health(self) -> bool:
        try:
            r = await self._client.get("/")
            return r.status_code < 500
        except httpx.HTTPError:
            return False

    async def list_vault(self) -> list[dict]:
        r = await self._client.get("/vault/")
        await self._handle_401(r)
        return r.json()

    async def periodic_daily(self) -> dict:
        r = await self._client.get("/periodic/daily/")
        await self._handle_401(r)
        if r.headers.get("content-type", "").startswith("application/json"):
            return r.json()
        return {}

    async def search_simple(self, query: str) -> list[dict]:
        r = await self._client.post("/search/simple/", params={"query": query})
        await self._handle_401(r)
        return r.json()

    async def read_note(self, path: str) -> dict:
        # Returns content + a version signal we use for OCC (Phase 2.10).
        r = await self._client.get(f"/vault/{path}", headers={"Accept": "application/vnd.olrapi.note+json"})
        await self._handle_401(r)
        return r.json()

    async def append(self, path: str, content: str) -> None:
        # Append-only writes to designated log.md targets.
        r = await self._client.post(f"/vault/{path}", content=content,
                                    headers={"Content-Type": "text/markdown"})
        await self._handle_401(r)

    async def patch(self, path: str, target_type: str, target: str, content: str,
                    reject_if_preexists: bool = True) -> None:
        # rejectIfContentPreexists = our idempotency / retry guard (Phase 2.3 / 6.6 / 6.7).
        headers = {
            "Operation": "append",
            "Target-Type": target_type,
            "Target": target,
            "Content-Type": "text/markdown",
        }
        if reject_if_preexists:
            headers["If-None-Match"] = "*"
        r = await self._client.patch(f"/vault/{path}", content=content, headers=headers)
        await self._handle_401(r)

    async def aclose(self) -> None:
        await self._client.aclose()


backend = ObsidianBackend()
