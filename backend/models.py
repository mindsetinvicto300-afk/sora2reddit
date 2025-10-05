from __future__ import annotations

from pydantic import BaseModel


class CodeEntry(BaseModel):
    code: str
    comment_id: str
    author: str | None
    permalink: str
    created_utc: float
    first_seen: float


class CodesResponse(BaseModel):
    codes: list[CodeEntry]
    fetched_at: float
