"""
analysis.py  –  Data analysis & chart generation
==================================================
Educational Keystroke Logger Demo – DO NOT USE MALICIOUSLY

Provides:
  - top_keys()         → List of (key, count) sorted by frequency
  - generate_charts()  → Dict of base64-encoded PNG chart images
"""

import base64
import io
import time
from typing import Any, Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")          # non-interactive backend – no Tkinter conflict
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------

def top_keys(
    records: List[Dict[str, Any]], n: int = 15
) -> List[Tuple[str, int]]:
    """Return the *n* most frequent keys as (key, count) pairs."""
    freq: Dict[str, int] = {}
    for rec in records:
        k = rec.get("key", "?")
        freq[k] = freq.get(k, 0) + 1
    sorted_keys = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return sorted_keys[:n]


def compute_kpm_over_time(
    records: List[Dict[str, Any]], bucket_secs: int = 10
) -> Tuple[List[str], List[float]]:
    """
    Compute keystrokes-per-minute over time by bucketing records.

    Returns
    -------
    labels  – list of human-readable time labels (MM:SS from session start)
    values  – list of KPM values per bucket
    """
    if not records:
        return [], []

    timestamps = sorted(r["timestamp"] for r in records if "timestamp" in r)
    if not timestamps:
        return [], []

    t_start  = timestamps[0]
    t_end    = timestamps[-1]
    duration = t_end - t_start

    if duration == 0:
        return ["0:00"], [len(records) * 6.0]   # rough estimate for one-shot

    buckets: Dict[int, int] = {}
    for ts in timestamps:
        bucket_idx = int((ts - t_start) / bucket_secs)
        buckets[bucket_idx] = buckets.get(bucket_idx, 0) + 1

    max_bucket = max(buckets.keys())
    labels, values = [], []
    for i in range(max_bucket + 1):
        count = buckets.get(i, 0)
        kpm   = (count / bucket_secs) * 60
        elapsed_s = i * bucket_secs
        labels.append(f"{elapsed_s // 60}:{elapsed_s % 60:02d}")
        values.append(round(kpm, 2))

    return labels, values


# ---------------------------------------------------------------------------
# Chart generation  (returns base64 strings so FastAPI can serve them as JSON)
# ---------------------------------------------------------------------------

def _fig_to_b64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _apply_dark_theme() -> None:
    plt.rcParams.update({
        "figure.facecolor":  "#1a1a2e",
        "axes.facecolor":    "#16213e",
        "axes.edgecolor":    "#0f3460",
        "axes.labelcolor":   "#e0e0e0",
        "xtick.color":       "#a0a0b0",
        "ytick.color":       "#a0a0b0",
        "text.color":        "#e0e0e0",
        "grid.color":        "#0f3460",
        "grid.linestyle":    "--",
        "grid.alpha":        0.5,
        "font.family":       "DejaVu Sans",
        "font.size":         10,
    })


def generate_bar_chart(records: List[Dict[str, Any]]) -> str:
    """Bar chart: top 15 most frequent keys."""
    _apply_dark_theme()
    data = top_keys(records, n=15)
    if not data:
        return ""

    keys, counts = zip(*data)

    palette = sns.color_palette("mako", len(keys))
    fig, ax  = plt.subplots(figsize=(10, 5))
    bars     = ax.barh(list(keys)[::-1], list(counts)[::-1], color=list(palette)[::-1])

    ax.set_title("Top 15 Most Frequent Keys", fontsize=14, pad=12, color="#e94560")
    ax.set_xlabel("Count", labelpad=8)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.grid(axis="x")

    for bar, cnt in zip(bars, list(counts)[::-1]):
        ax.text(
            bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
            str(cnt), va="center", fontsize=9, color="#e0e0e0"
        )

    fig.tight_layout()
    return _fig_to_b64(fig)


def generate_kpm_chart(records: List[Dict[str, Any]]) -> str:
    """Line chart: keystrokes per minute over time."""
    _apply_dark_theme()
    labels, values = compute_kpm_over_time(records)
    if not labels:
        return ""

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(labels, values, color="#e94560", linewidth=2, marker="o", markersize=4)
    ax.fill_between(range(len(values)), values, alpha=0.15, color="#e94560")
    ax.set_title("Typing Speed (KPM) Over Time", fontsize=14, pad=12, color="#e94560")
    ax.set_xlabel("Elapsed Time (min:sec)", labelpad=8)
    ax.set_ylabel("Keystrokes / min", labelpad=8)

    step = max(1, len(labels) // 10)
    ax.set_xticks(range(0, len(labels), step))
    ax.set_xticklabels(labels[::step], rotation=30, ha="right", fontsize=8)
    ax.grid(axis="y")

    fig.tight_layout()
    return _fig_to_b64(fig)


def generate_pie_chart(records: List[Dict[str, Any]]) -> str:
    """Pie chart: regular vs. special key ratio."""
    _apply_dark_theme()
    regular = sum(1 for r in records if not r.get("is_special", False))
    special  = len(records) - regular
    if regular + special == 0:
        return ""

    fig, ax = plt.subplots(figsize=(6, 6))
    wedges, texts, autotexts = ax.pie(
        [regular, special],
        labels=["Regular Keys", "Special Keys"],
        autopct="%1.1f%%",
        colors=["#0f3460", "#e94560"],
        startangle=140,
        textprops={"color": "#e0e0e0"},
    )
    for at in autotexts:
        at.set_color("#ffffff")
        at.set_fontsize(11)

    ax.set_title("Key Type Distribution", fontsize=14, pad=12, color="#e94560")
    fig.tight_layout()
    return _fig_to_b64(fig)


def generate_all_charts(records: List[Dict[str, Any]]) -> Dict[str, str]:
    """Generate all charts and return a dict of {name: base64_png}."""
    return {
        "bar":  generate_bar_chart(records),
        "kpm":  generate_kpm_chart(records),
        "pie":  generate_pie_chart(records),
    }
