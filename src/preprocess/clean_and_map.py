from __future__ import annotations

import io
from pathlib import Path

import pandas as pd


def load_csv_safely(path: Path) -> pd.DataFrame:
    """Safely load CSV files, skipping comment blocks and handling URLhaus format."""
    with open(path, encoding="utf-8", errors="ignore") as f:
        lines = []
        header_idx = -1
        for idx in range(100):
            line = f.readline()
            if not line:
                break
            lines.append(line)
            clean_line = line.strip()
            if "id,dateadded,url" in clean_line or "url,url_status" in clean_line:
                header_idx = idx
                break
            if not clean_line.startswith("#") and header_idx == -1:
                header_idx = idx
                break

    if header_idx != -1 and "id,dateadded,url" in lines[header_idx]:
        with open(path, encoding="utf-8", errors="ignore") as f:
            full_content = f.read()
        header_offset = full_content.find("# id,dateadded,url")
        if header_offset != -1:
            clean_content = full_content[header_offset:].lstrip("#")
            return pd.read_csv(io.StringIO(clean_content), on_bad_lines="skip")

    return pd.read_csv(path, on_bad_lines="skip", engine="python")


def is_url_file(path: Path) -> bool:
    """Classify if a raw dataset file is a URL dataset."""
    path_str = str(path).lower()
    if "url datasets" in path_str or "url_cleaned" in path_str:
        return True
    if "email datasets" in path_str:
        return False
    if any(k in path_str for k in ["url", "phishtank", "majestic", "tranco", "top-1m"]):
        return True
    return False


def _get_columns(df: pd.DataFrame) -> tuple[str | None, str]:
    """Safely find the text/url and label columns regardless of schema."""
    label_col = None
    text_col = None

    for c in df.columns:
        c_lower = str(c).lower()
        if any(t in c_lower for t in ["label", "status", "type", "class", "target", "verified"]):
            label_col = c
            break

    # Prioritize selecting actual content columns and avoid metadata IDs/counts/lengths
    for c in df.columns:
        c_lower = str(c).lower()
        if c == label_col:
            continue
        if any(
            bad in c_lower
            for bad in ["id", "file", "path", "rank", "index", "count", "ratio", "length", "len"]
        ):
            continue
        if any(
            t in c_lower for t in ["text", "url", "body", "content", "message", "email", "domain"]
        ):
            text_col = c
            break

    # Fallback to any column that isn't label_col or metadata-like
    if not text_col:
        for c in df.columns:
            c_lower = str(c).lower()
            if c == label_col:
                continue
            if not any(
                bad in c_lower
                for bad in [
                    "id",
                    "file",
                    "path",
                    "rank",
                    "index",
                    "count",
                    "ratio",
                    "length",
                    "len",
                ]
            ):
                text_col = c
                break

    if (not label_col or not text_col) and len(df.columns) == 2:
        c1, c2 = df.columns
        if df[c1].nunique() < df[c2].nunique():
            label_col, text_col = c1, c2
        else:
            label_col, text_col = c2, c1

    if not label_col:
        label_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
    if not text_col:
        remaining = [c for c in df.columns if c != label_col]
        text_col = remaining[0] if remaining else df.columns[0]

    return text_col, label_col


def prepare_url_data() -> None:
    """Scan and process all URL raw CSV datasets, normalize URLs, map classes, and output a balanced CSV dataset."""
    print("Preparing URL Data...")

    label_map = {
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

    all_csvs = list(Path("data/raw").rglob("*.csv"))
    # Exclude feature-only datasets
    all_csvs = [f for f in all_csvs if "iscx-url-2016" not in str(f).lower()]
    url_files = [f for f in all_csvs if is_url_file(f)]
    if not url_files:
        print("Skipping URL data: No URL files found in data/raw/.")
        return

    dfs = []
    for raw_url_path in url_files:
        print(f"Processing URL dataset: {raw_url_path}")
        try:
            df = load_csv_safely(raw_url_path)
        except Exception as e:
            print(f"Failed to load {raw_url_path}: {e}")
            continue

        filename = raw_url_path.name.lower()
        if "majestic" in filename:
            url_series = df["Domain"]
            label_series = pd.Series(0, index=df.index)
        elif "tranco" in filename or "top-1m" in filename:
            url_series = df.iloc[:, 1]
            label_series = pd.Series(0, index=df.index)
        elif len(df.columns) == 1:
            url_series = df.iloc[:, 0]
            label_series = pd.Series(1, index=df.index)
        else:
            raw_text_col, raw_label_col = _get_columns(df)
            if not raw_text_col:
                print(f"  -> Skipping {raw_url_path.name}: no valid text column found.")
                continue
            url_series = df[raw_text_col]
            if isinstance(url_series, pd.DataFrame):
                url_series = url_series.iloc[:, 0]

            label_series = df[raw_label_col]
            if isinstance(label_series, pd.DataFrame):
                label_series = label_series.iloc[:, 0]

        df = pd.DataFrame({"url": url_series, "label": label_series})

        # Unconditionally map the labels to ensure consistent parsing across different schemas
        df["label"] = df["label"].astype(str).str.lower().str.strip().map(label_map)

        # Clean up
        df["url"] = df["url"].astype(str).str.lower()
        df = df[["url", "label"]].dropna().drop_duplicates()
        df["label"] = df["label"].astype(int)
        dfs.append(df)

    if not dfs:
        print("No URL data to save.")
        return

    df_url = pd.concat(dfs, ignore_index=True).drop_duplicates(subset=["url"])

    # Save cleaned but unbalanced URL dataset first
    out_path_unbalanced = Path("data/processed/url_cleaned_unbalanced.csv")
    out_path_unbalanced.parent.mkdir(parents=True, exist_ok=True)
    df_url.to_csv(out_path_unbalanced, index=False)
    print(f"Saved {len(df_url)} cleaned (unbalanced) URLs to {out_path_unbalanced}")

    # Balance URL classes via random undersampling
    print("\nBalancing URL dataset via random undersampling...")
    min_size = df_url["label"].value_counts().min()
    df_url_balanced = (
        df_url.groupby("label").sample(n=min_size, random_state=42).reset_index(drop=True)
    )

    out_path = Path("data/processed/url_cleaned.csv")
    df_url_balanced.to_csv(out_path, index=False)
    print(f"Saved {len(df_url_balanced)} cleaned and balanced URLs to {out_path}")


def prepare_email_data() -> None:
    """Scan and process all email raw CSV datasets, parse bodies, map labels (Legitimate/Spam/Phishing), balance classes, and output the cleaned dataset."""
    print("\nPreparing Email Data...")
    label_map = {
        "legitimate": 0,
        "safe": 0,
        "safe email": 0,
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

    all_csvs = list(Path("data/raw").rglob("*.csv"))
    # Exclude non-text/metadata-only email/spam files and feature-only URL files
    all_csvs = [
        f
        for f in all_csvs
        if "iscx-url-2016" not in str(f).lower()
        and "it4lia_phishingemailcurateddatasets_cleaned.csv" not in f.name.lower()
    ]
    url_files = [f for f in all_csvs if is_url_file(f)]
    email_files = [f for f in all_csvs if f not in url_files]

    dfs = []
    for raw_email_path in email_files:
        print(f"Processing Email dataset: {raw_email_path}")

        try:
            df = load_csv_safely(raw_email_path)
        except Exception as e:
            print(f"Failed to load {raw_email_path}: {e}")
            continue

        if len(df.columns) == 1:
            text_series = df.iloc[:, 0]
            label_series = pd.Series(2, index=df.index)
        else:
            raw_text_col, raw_label_col = _get_columns(df)
            if not raw_text_col:
                print(f"  -> Skipping {raw_email_path.name}: no valid text column found.")
                continue
            text_series = df[raw_text_col]
            if isinstance(text_series, pd.DataFrame):
                text_series = text_series.iloc[:, 0]

            label_series = df[raw_label_col]
            if isinstance(label_series, pd.DataFrame):
                label_series = label_series.iloc[:, 0]

        df = pd.DataFrame({"text": text_series, "label": label_series})

        print(f"  -> Raw labels found: {df['label'].unique().tolist()}")

        # Apply lowercasing to the email text as part of preprocessing
        df["text"] = df["text"].astype(str).str.lower()

        # Unconditionally map the labels to ensure consistent parsing across different schemas
        df["label"] = df["label"].astype(str).str.lower().str.strip().map(label_map)

        # If this is a phishing dataset, its positive class (1) means Phishing (2), not Spam (1)
        if any(
            kw in raw_email_path.name.lower() for kw in ["nazario", "phishing", "fraud", "nigerian"]
        ):
            df["label"] = df["label"].replace({1: 2})

        print(f"  -> Mapped labels: {df['label'].dropna().unique().tolist()}")

        df = df[["text", "label"]].dropna().drop_duplicates()
        df["label"] = df["label"].astype(int)
        dfs.append(df)

    if not dfs:
        print("No email data to save.")
        return

    # Combine all email datasets and remove any cross-dataset duplicates
    df_email = pd.concat(dfs, ignore_index=True).drop_duplicates(subset=["text"])

    # Keep natural distribution and shuffle
    print("\nSkipping email dataset downsampling to retain all unique text data.")
    df_email = df_email.sample(frac=1, random_state=42).reset_index(drop=True)

    out_path = Path("data/processed/email_cleaned.csv")
    df_email.to_csv(out_path, index=False)
    print(f"Saved {len(df_email)} cleaned Emails to {out_path}")


if __name__ == "__main__":
    prepare_url_data()
    prepare_email_data()
