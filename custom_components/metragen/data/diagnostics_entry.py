"""Seção tipada da entry no dump de diagnóstico."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping


class MetragenDiagnosticsEntry(TypedDict):
    """Seção da entry no dump de diagnóstico."""

    title: str
    version: int
    domain: str
    data: Mapping[str, str]
    options: Mapping[str, str | int]
