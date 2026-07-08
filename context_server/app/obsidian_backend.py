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

    async def health(self) -> bool:
        try:
            r = await self._client.get("/")
            return r.status_code < 500
        except httpx.HTTPError:
            return False

    async def search_simple(self, query: str) -> list[dict]:
        r = await self._client.post("/search/simple/", params={"query": query})
        r.raise_for_status()
        return r.json()

    async def read_note(self, path: str) -> dict:
        # Returns content + a version signal we use for OCC (Phase 2.10).
        r = await self._client.get(f"/vault/{path}", headers={"Accept": "application/vnd.olrapi.note+json"})
        r.raise_for_status()
        return r.json()

    async def append(self, path: str, content: str) -> None:
        # Append-only writes to designated log.md targets.
        r = await self._client.post(f"/vault/{path}", content=content,
                                    headers={"Content-Type": "text/markdown"})
        r.raise_for_status()

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
        r.raise_for_status()

    async def aclose(self) -> None:
        await self._client.aclose()


backend = ObsidianBackend()
