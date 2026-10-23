from __future__ import annotations

import html
from math import floor, log10
from typing import Iterable

from ui.components import class_color


def _number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def nice_max(value: float) -> float:
    """Return a 1/2/5/10-step axis maximum at or above value."""
    if value <= 0:
        return 1
    magnitude = 10 ** floor(log10(value))
    fraction = value / magnitude
    step = 1 if fraction <= 1 else 2 if fraction <= 2 else 5 if fraction <= 5 else 10
    return step * magnitude


def bar_path(x: float, y: float, width: float, height: float, radius: float) -> str:
    radius = max(0, min(radius, width / 2, height))
    right = x + width
    bottom = y + height
    return (
        f"M {_number(x)} {_number(bottom)} "
        f"L {_number(x)} {_number(y + radius)} "
        f"Q {_number(x)} {_number(y)} {_number(x + radius)} {_number(y)} "
        f"L {_number(right - radius)} {_number(y)} "
        f"Q {_number(right)} {_number(y)} {_number(right)} {_number(y + radius)} "
        f"L {_number(right)} {_number(bottom)} Z"
    )


def bar_list(items: Iterable[tuple[str, int]]) -> str:
    values = sorted(items, key=lambda item: (-item[1], item[0].casefold()))
    width, row_height = 800, 38
    height = max(56, 24 + len(values) * row_height)
    maximum = max((count for _, count in values), default=0)
    scale = max(1, maximum)
    content = []
    if not values:
        content.append(
            '<text x="16" y="34" fill="var(--muted)" font-size="13">No detections</text>'
        )
    for index, (name, count) in enumerate(values):
        y = 20 + index * row_height
        color = class_color(name)
        safe_name = html.escape(name)
        bar_width = 430 * count / scale
        share = (100 * count / sum(value for _, value in values)) if sum(
            value for _, value in values
        ) else 0
        content.append(
            f'<g><title>{safe_name}: {count} objects ({share:.1f}%)</title>'
            f'<rect x="0" y="{y - 10}" width="{width}" height="28" fill="transparent"/>'
            f'<rect x="8" y="{y}" width="8" height="8" rx="1" fill="{color}"/>'
            f'<text x="25" y="{y + 8}" fill="var(--text-2)" font-size="13">{safe_name}</text>'
            f'<rect x="190" y="{y - 2}" width="430" height="12" rx="1" fill="var(--panel-3)"/>'
            f'<rect x="190" y="{y - 2}" width="{_number(bar_width)}" height="12" rx="1" fill="{color}"/>'
            f'<text x="640" y="{y + 8}" fill="var(--text)" font-size="13">{count}</text>'
            f'<text x="690" y="{y + 8}" fill="var(--muted)" font-size="12">{share:.1f}%</text>'
            "</g>"
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        'width="100%" role="img" aria-label="Tracked objects by class">'
        + "".join(content)
        + "</svg>"
    )


def histogram(buckets: Iterable[tuple[str, int]]) -> str:
    values = list(buckets)
    width, height = 800, 250
    left, right, top, bottom = 48, 16, 24, 42
    plot_width, plot_height = width - left - right, height - top - bottom
    y_max = nice_max(max((value for _, value in values), default=0))
    tick_count = 4
    elements = []
    for tick in range(tick_count + 1):
        value = y_max * tick / tick_count
        y = top + plot_height * (1 - tick / tick_count)
        elements.append(
            f'<line x1="{left}" y1="{_number(y)}" x2="{width - right}" y2="{_number(y)}" '
            'stroke="var(--line-2)" stroke-width="1"/>'
            f'<text x="{left - 8}" y="{_number(y + 4)}" text-anchor="end" '
            f'fill="var(--muted)" font-size="10">{_number(value)}</text>'
        )
    if values:
        slot = plot_width / len(values)
        bar_width = slot * 0.62
        for index, (label, value) in enumerate(values):
            bar_height = plot_height * value / y_max
            x = left + index * slot + (slot - bar_width) / 2
            y = top + plot_height - bar_height
            safe_label = html.escape(label)
            elements.append(
                f'<g><title>{safe_label}: {value} first-seen objects</title>'
                f'<path d="{bar_path(x, y, bar_width, bar_height, 4)}" fill="var(--text-2)"/>'
                f'<text x="{_number(x + bar_width / 2)}" y="{height - 18}" '
                f'text-anchor="middle" fill="var(--muted)" font-size="10">{safe_label}</text></g>'
            )
    else:
        elements.append(
            f'<text x="{left + plot_width / 2}" y="{top + plot_height / 2}" '
            'text-anchor="middle" fill="var(--muted)" font-size="13">No detections</text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        'width="100%" role="img" aria-label="Five-second object timeline">'
        + "".join(elements)
        + "</svg>"
    )


def stacked_bar(items: Iterable[tuple[str, int]]) -> str:
    values = [(name, count) for name, count in items if count > 0]
    width, height = 800, 72
    total = sum(count for _, count in values)
    x = 0.0
    elements = []
    for name, count in values:
        segment_width = width * count / total if total else 0
        share = 100 * count / total if total else 0
        safe_name = html.escape(name)
        elements.append(
            f'<g><title>{safe_name}: {count} objects ({share:.1f}%)</title>'
            f'<rect x="{_number(x)}" y="12" width="{_number(segment_width)}" height="28" '
            f'fill="{class_color(name)}"/>'
            f'<text x="{_number(x + segment_width / 2)}" y="60" text-anchor="middle" '
            'fill="var(--text-2)" font-size="11">'
            f'{safe_name} {share:.1f}%</text></g>'
        )
        x += segment_width
    if not values:
        elements.append(
            '<text x="0" y="30" fill="var(--muted)" font-size="12">No detections</text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        'width="100%" role="img" aria-label="Class mix">'
        + "".join(elements)
        + "</svg>"
    )
