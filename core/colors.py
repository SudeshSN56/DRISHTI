"""Deterministic class-to-colour mapping shared by API, report, and UI layers."""
from __future__ import annotations

import hashlib


CLASS_COLORS = {
    "person": "#fab219",
    "car": "#6b9bea",
    "truck": "#ec835a",
    "bus": "#d03b3b",
    "bicycle": "#3fb26b",
    "motorcycle": "#b07be0",
    "boat": "#4cc3d9",
    "bird": "#c8d96b",
    "dog": "#e08fb4",
    "cat": "#e0b48f",
    "horse": "#8f9be0",
    "cow": "#9bc48f",
    "sheep": "#c4c4c4",
}


def class_color(class_name: str) -> str:
    """Return a fixed hex colour for known classes or a deterministic HSL for others."""
    known = CLASS_COLORS.get(class_name.casefold())
    if known:
        return known
    digest = hashlib.sha256(class_name.casefold().encode("utf-8")).digest()
    hue = int.from_bytes(digest[:2], "big") % 360
    return f"hsl({hue} 58% 62%)"
