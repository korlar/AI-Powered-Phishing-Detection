"""Visualize original vs. cleaned/balanced dataset distributions with pie charts.

Generates pie charts saved to reports/:
  1. Email – Original distribution  (Legitimate / Spam / Phishing)
  2. Email – After cleaning          (Legitimate / Spam / Phishing)
  3. URL   – Original distribution  (Legitimate / Malicious)
  4. URL   – After cleaning          (Legitimate / Malicious)
  5. URL   – After undersampling     (Legitimate / Malicious)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# ── Label mappings (mirrors clean_and_map.py) ──────────────────────────

EMAIL_LABEL_MAP = {
    "legitimate": 0,
    "legitimate email": 0,
    "ham": 0,
    "benign": 0,
    "spam": 1,
    "phishing": 2,
    "phishing email": 2,
    "malware": 2,
    "0": 0,
    "1": 1,
    "2": 2,
    "0.0": 0,
    "1.0": 1,
    "2.0": 2,
}

URL_LABEL_MAP = {
    "legitimate": 0,
    "benign": 0,
    "phishing": 1,
    "malware": 1,
    "defacement": 1,
    "spam": 1,
    "0": 0,
    "1": 1,
    "2": 1,
    "3": 1,
    "4": 1,
    "0.0": 0,
    "1.0": 1,
    "yes": 1,
    "valid": 1,
}


def _find_label_col(columns: list[str]) -> str | None:
    """Find the label column name from a list of column names."""
    for c in columns:
        if any(
            t in str(c).lower() for t in ["label", "status", "type", "class", "target", "verified"]
        ):
            return c
    return None


def _fast_count_labels(path: Path, label_map: dict, is_phishing_source: bool = False) -> pd.Series:
    """Efficiently count mapped labels from a CSV by reading only the label column."""
    try:
        # Peek at columns first
        peek = pd.read_csv(path, nrows=0, engine="python", on_bad_lines="skip")
        cols = list(peek.columns)
    except Exception as e:
        print(f"  ⚠ Skipping {path.name}: {e}")
        return pd.Series(dtype=int)

    label_col = _find_label_col(cols)

    if len(cols) == 1:
        # Single-column file (blocklist) — all rows are one label
        with open(path, encoding="utf-8", errors="ignore") as f:
            n_rows = sum(1 for _ in f) - 1
        if is_phishing_source:
            return pd.Series({2: max(n_rows, 0)})
        return pd.Series({1: max(n_rows, 0)})

    if not label_col:
        # Fallback: use second column if only 2 columns, otherwise skip
        if len(cols) == 2:
            label_col = cols[1]
        else:
            print(f"  ⚠ Skipping {path.name}: cannot identify label column in {cols}")
            return pd.Series(dtype=int)

    try:
        labels = pd.read_csv(path, usecols=[label_col], engine="python", on_bad_lines="skip")
    except Exception as e:
        print(f"  ⚠ Skipping {path.name}: {e}")
        return pd.Series(dtype=int)

    mapped = (
        labels[label_col].astype(str).str.lower().str.strip().map(label_map).dropna().astype(int)
    )

    if is_phishing_source:
        mapped = mapped.replace({1: 2})

    return mapped.value_counts()


def _count_original_emails() -> pd.Series:
    """Return label counts for the *original* email data (fast, label-column only)."""
    all_csvs = list(Path("data/raw").rglob("*.csv"))
    url_files = {f for f in all_csvs if "url" in str(f).lower() or "phishtank" in str(f).lower()}
    email_files = [f for f in all_csvs if f not in url_files]

    totals: dict[int, int] = {}
    for path in email_files:
        is_phishing = any(
            kw in path.name.lower() for kw in ["nazario", "phishing", "fraud", "nigerian"]
        )
        print(f"  📧 {path.name} {'(phishing source)' if is_phishing else ''}")
        counts = _fast_count_labels(path, EMAIL_LABEL_MAP, is_phishing_source=is_phishing)
        for k, v in counts.items():
            totals[k] = totals.get(k, 0) + v

    return pd.Series(totals).sort_index()


def _count_original_urls() -> pd.Series:
    """Return label counts for the *original* URL data (fast, label-column only)."""
    all_csvs = list(Path("data/raw").rglob("*.csv"))
    url_files = [f for f in all_csvs if "url" in str(f).lower() or "phishtank" in str(f).lower()]

    totals: dict[int, int] = {}
    for path in url_files:
        print(f"  🔗 {path.name}")
        counts = _fast_count_labels(path, URL_LABEL_MAP)
        for k, v in counts.items():
            totals[k] = totals.get(k, 0) + v

    return pd.Series(totals).sort_index()


# ── Pie-chart drawing ──────────────────────────────────────────────────

EMAIL_COLORS = {0: "#4FC3F7", 1: "#FFB74D", 2: "#EF5350"}  # Legitimate / Spam / Phishing
EMAIL_NAMES = {0: "Legitimate", 1: "Spam", 2: "Phishing"}

URL_COLORS = {0: "#66BB6A", 1: "#EF5350"}  # Legitimate / Malicious
URL_NAMES = {0: "Legitimate", 1: "Malicious"}


def _draw_pie(
    ax: plt.Axes,
    counts: pd.Series,
    color_map: dict[int, str],
    name_map: dict[int, str],
    title: str,
) -> None:
    """Draw a single pie chart on *ax*."""
    labels = [f"{name_map[k]}  ({counts[k]:,})" for k in counts.index]
    colors = [color_map[k] for k in counts.index]

    wedges, texts, autotexts = ax.pie(
        counts.values,
        labels=labels,
        colors=colors,
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.55,
        textprops={"fontsize": 11, "fontweight": "bold"},
        wedgeprops={"edgecolor": "white", "linewidth": 2},
    )
    for at in autotexts:
        at.set_fontsize(10)
        at.set_color("white")
        at.set_fontweight("bold")

    ax.set_title(title, fontsize=14, fontweight="bold", pad=16)


# ── Main entry-point ───────────────────────────────────────────────────


def main() -> None:
    out_dir = Path("reports")
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---------- EMAIL PIE CHARTS ----------
    print("Computing original email distribution …")
    orig_email = _count_original_emails()
    print(f"\n  Original email counts:\n{orig_email}\n")

    # Cleaned email counts (from the cleaned file)
    cleaned_email = pd.read_csv("data/processed/email_cleaned.csv", usecols=["label"])
    clean_email_counts = cleaned_email["label"].value_counts().sort_index()
    print(f"  Cleaned email counts:\n{clean_email_counts}\n")

    fig_email, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    fig_email.suptitle("Email Dataset Distribution", fontsize=18, fontweight="bold", y=1.02)

    _draw_pie(
        ax1, orig_email, EMAIL_COLORS, EMAIL_NAMES, "Original (Before Cleaning & Deduplication)"
    )
    _draw_pie(ax2, clean_email_counts, EMAIL_COLORS, EMAIL_NAMES, "Cleaned (After Dedup & Mapping)")

    fig_email.tight_layout()
    email_path = out_dir / "email_distribution_pie.png"
    fig_email.savefig(email_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig_email)
    print(f"✅ Saved → {email_path}")

    # ---------- URL PIE CHARTS ----------
    print("\nComputing original URL distribution …")
    orig_url = _count_original_urls()
    print(f"\n  Original URL counts:\n{orig_url}\n")

    cleaned_url = pd.read_csv("data/processed/url_cleaned_unbalanced.csv", usecols=["label"])
    clean_url_counts = cleaned_url["label"].value_counts().sort_index()
    print(f"  Cleaned URL counts:\n{clean_url_counts}\n")

    balanced_url = pd.read_csv("data/processed/url_cleaned.csv", usecols=["label"])
    bal_url_counts = balanced_url["label"].value_counts().sort_index()
    print(f"  Balanced URL counts:\n{bal_url_counts}\n")

    fig_url, (ax3, ax4, ax5) = plt.subplots(1, 3, figsize=(21, 7))
    fig_url.suptitle("URL Dataset Distribution", fontsize=18, fontweight="bold", y=1.02)

    _draw_pie(ax3, orig_url, URL_COLORS, URL_NAMES, "Original (All Raw Sources)")
    _draw_pie(ax4, clean_url_counts, URL_COLORS, URL_NAMES, "Cleaned (After Dedup & Mapping)")
    _draw_pie(ax5, bal_url_counts, URL_COLORS, URL_NAMES, "Balanced (After Undersampling)")

    fig_url.tight_layout()
    url_path = out_dir / "url_distribution_pie.png"
    fig_url.savefig(url_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig_url)
    print(f"✅ Saved → {url_path}")


if __name__ == "__main__":
    main()
