"""Observed-attempt heatmap helpers for Glitch Gate.

Only measured *game attempts* populate a cell; untried cells are never inferred
or calculated. In particular, the charts do not leak the hidden target cycle.
"""
from __future__ import annotations

STATUS_CODE = {"NORMAL": 1, "RESET": 2, "SUCCESS": 3}


def observed_grid(attempts: list[dict], x_field: str, y_field: str,
                  x_values: list[int | float], y_values: list[int | float],
                  filters: dict | None = None) -> tuple[list[list[int]], list[list[str]]]:
    """Return (status grid, hover labels) from recorded attempts only.

    Multiple attempts in the same cell show the latest actual result. A status
    value of 0 means the combination has not been tested (not predicted NORMAL).
    """
    filters = filters or {}
    x_index = {round(float(v), 4): i for i, v in enumerate(x_values)}
    y_index = {round(float(v), 4): i for i, v in enumerate(y_values)}
    matrix = [[0 for _ in x_values] for _ in y_values]
    texts = [["Not tested" for _ in x_values] for _ in y_values]

    for item in attempts:
        if any(round(float(item.get(k, -999)), 4) != round(float(v), 4)
               for k, v in filters.items()):
            continue
        xi = x_index.get(round(float(item[x_field]), 4))
        yi = y_index.get(round(float(item[y_field]), 4))
        if xi is None or yi is None:
            continue
        matrix[yi][xi] = STATUS_CODE[item["status"]]
        texts[yi][xi] = (
            f"Attempt #{item['attempt']}<br>Result: {item['status']}<br>"
            f"ext_offset: {item['ext_offset']}<br>"
            f"offset: {item['offset_ns']:.2f} model ns<br>"
            f"width: {item['width_ns']:.2f} model ns"
        )
    return matrix, texts


def focused_range(values: list[int | float], observed: list[int | float],
                  padding: float, focus: bool) -> list[int | float]:
    """Zoom only from observed inputs, never from hidden target parameters."""
    if not focus or not observed:
        return values
    lo = min(observed) - padding - 1e-6
    hi = max(observed) + padding + 1e-6
    return [v for v in values if lo <= v <= hi]
