"""
Long synchronous work (1 to 3 minutes) behind a reverse proxy and a tunnel: stream a keepalive
byte every few seconds, then the JSON body. Leading whitespace is valid JSON, so clients parse
the body normally. Errors arrive as {"detail": ..., "status": ...} inside the 200 stream because
the status line has already been sent.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

log = logging.getLogger("longrun")
KEEPALIVE_SECONDS = 8


def stream_json(work: Callable[[], BaseModel]) -> StreamingResponse:
    """`work` runs in a worker thread (it may block on network calls) and returns a Pydantic model."""

    async def generate():
        task = asyncio.create_task(asyncio.to_thread(work))
        while True:
            done, _ = await asyncio.wait({task}, timeout=KEEPALIVE_SECONDS)
            if done:
                break
            yield " "
        try:
            result = task.result()
        except HTTPException as exc:
            yield json.dumps({"detail": exc.detail, "status": exc.status_code})
            return
        except Exception as exc:  # surfaced to the client instead of a dropped connection
            log.exception("long-running request failed")
            yield json.dumps({"detail": f"{type(exc).__name__}: {exc}", "status": 500})
            return
        yield result.model_dump_json()

    return StreamingResponse(generate(), media_type="application/json", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
