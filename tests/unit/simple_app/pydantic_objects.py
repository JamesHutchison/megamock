from __future__ import annotations

from pydantic import BaseModel


class Parent(BaseModel):
    child: Child | None = None


class Child(BaseModel):
    attribute: str
