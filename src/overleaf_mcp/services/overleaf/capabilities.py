"""
Probes for optional, CEP-specific server capabilities.

CEP reimplements SaaS/Server-Pro-only features independently, so a given
feature's presence (and API shape) can't be assumed from configuration —
it has to be detected live, once, at server startup. Keep each probe here
narrow and cheap: it runs on every startup.
"""

import httpx

_PROBE_PROJECT_ID = "0" * 24


async def supports_review_mode(client: httpx.AsyncClient) -> bool:
    """
    Probe whether the server exposes CEP's review-mode (track changes)
    routes. A GET against a syntactically valid but nonexistent project id
    is enough to distinguish: the route 404s on vanilla CE (the module is
    entirely absent) and returns some other status (401/403 — access
    denied, but the route exists) on CEP. Verified live against both
    outcomes.
    :return:
    """
    try:
        response = await client.get(f"/project/{_PROBE_PROJECT_ID}/ranges")
    except httpx.HTTPError:
        return False
    return response.status_code != 404
