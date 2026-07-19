import re
from collections import Counter
from pathlib import Path

import pandas as pd

# Basic English stop words to filter out noise from top words analysis
STOP_WORDS = {
    "the",
    "and",
    "to",
    "of",
    "a",
    "in",
    "for",
    "is",
    "on",
    "that",
    "by",
    "this",
    "with",
    "i",
    "you",
    "it",
    "not",
    "or",
    "be",
    "are",
    "from",
    "at",
    "as",
    "your",
    "we",
    "have",
    "will",
    "an",
    "has",
    "can",
    "if",
}


def get_top_words(series: pd.Series, n: int = 10) -> list:
    all_text = " ".join(series.dropna().astype(str).tolist()).lower()
    words = re.findall(r"\b[a-z]{3,}\b", all_text)
    filtered_words = [w for w in words if w not in STOP_WORDS]
    return Counter(filtered_words).most_common(n)


def run_advanced_eda(file_path: Path):
    print("=" * 80)
    print(f"Analyzing {file_path.name}...\n")
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Error reading file: {e}\n")
        return

    print(f"Shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}\n")

    # Dynamically find the text/url and label columns
    label_cols = [
        c
        for c in df.columns
        if any(t in str(c).lower() for t in ["label", "status", "type", "class"])
    ]
    text_cols = [
        c
        for c in df.columns
        if any(
            t in str(c).lower()
            for t in ["text", "url", "body", "content", "message", "email", "domain"]
        )
    ]

    label_col = label_cols[0] if label_cols else None
    text_col = text_cols[0] if text_cols else None

    # Fallback for datasets with missing headers (e.g., columns are ['1', 'google.com'])
    if (not label_col or not text_col) and len(df.columns) == 2:
        c1, c2 = df.columns
        # The label column usually has very few unique values compared to the text/url column
        if df[c1].nunique() < df[c2].nunique():
            label_col, text_col = c1, c2
        else:
            label_col, text_col = c2, c1
        print(
            f"** Note: Missing headers detected. Guessed Label='{label_col}', Text='{text_col}' **\n"
        )

    # 1. Label Distribution
    if label_col:
        print(f"--- 1. Label Distribution ('{label_col}') ---")
        print(df[label_col].value_counts(dropna=False).to_string())
        print()

    if not text_col:
        print("--- Text Analysis --- \nNo clear text/url column found.\n")
        return

    # 2. Text Length Analysis
    print(f"--- 2. Text Length Analysis ('{text_col}') ---")
    df["char_count"] = df[text_col].fillna("").astype(str).apply(len)
    df["word_count"] = df[text_col].fillna("").astype(str).apply(lambda x: len(x.split()))
    print(
        f"Average Char Count: {df['char_count'].mean():.0f}  |  Max Char Count: {df['char_count'].max()}"
    )
    print(
        f"Average Word Count: {df['word_count'].mean():.0f}  |  Max Word Count: {df['word_count'].max()}\n"
    )

    # 3. Special Character & Embedded URL Analysis
    print("--- 3. Special Character & URL Analysis ---")
    df["has_url"] = (
        df[text_col]
        .fillna("")
        .astype(str)
        .apply(lambda x: bool(re.search(r"http[s]?://|www\.", x.lower())))
    )
    df["exclamation_count"] = df[text_col].fillna("").astype(str).apply(lambda x: x.count("!"))
    df["dollar_count"] = df[text_col].fillna("").astype(str).apply(lambda x: x.count("$"))
    print(
        f"Rows containing embedded links: {df['has_url'].sum()} ({(df['has_url'].sum() / len(df)) * 100:.1f}%)"
    )
    print(
        f"Average '!' count: {df['exclamation_count'].mean():.2f}  |  Average '$' count: {df['dollar_count'].mean():.2f}\n"
    )

    # 4. Top Words Analysis
    if label_col:
        print("--- 4. Top Words Analysis ---")
        # Identify phishing vs legitimate labels dynamically based on known datasets
        phish_labels = [
            v
            for v in df[label_col].unique()
            if str(v).lower() in ["phishing", "phishing email", "spam", "malware", "1", "2"]
        ]
        legit_labels = [
            v
            for v in df[label_col].unique()
            if str(v).lower() in ["legitimate", "safe", "safe email", "benign", "ham", "0"]
        ]

        if phish_labels:
            print(f"Top 10 words in '{phish_labels[0]}' class:")
            for word, count in get_top_words(df[df[label_col].isin(phish_labels)][text_col]):
                print(f"  {word}: {count}")

        if legit_labels:
            print(f"\nTop 10 words in '{legit_labels[0]}' class:")
            for word, count in get_top_words(df[df[label_col].isin(legit_labels)][text_col]):
                print(f"  {word}: {count}")
        print()


def run_eda():
    processed_dir = Path("data/processed")
    csv_files = list(processed_dir.glob("*_cleaned.csv"))

    if not csv_files:
        print(f"No CSV files found in {processed_dir}.")
        return

    print(f"Found {len(csv_files)} CSV files. Running Advanced EDA...\n")

    for file_path in csv_files:
        run_advanced_eda(file_path)


if __name__ == "__main__":
    run_eda()
