"""Formato tipado das opções graváveis pelo options flow."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class MetragenOptionsData(TypedDict, total=False):
    """Formato das opções graváveis pelo options flow."""

    scan_interval: NotRequired[int]
