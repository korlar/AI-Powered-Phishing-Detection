from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split


def build_splits(input_csv: Path, output_dir: Path, prefix: str, label_column: str) -> None:
    df = pd.read_csv(input_csv).drop_duplicates()
    train_df, temp_df = train_test_split(
        df, test_size=0.30, stratify=df[label_column], random_state=42
    )
    val_df, test_df = train_test_split(
        temp_df, test_size=0.50, stratify=temp_df[label_column], random_state=42
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    train_df.to_csv(output_dir / f"{prefix}_train.csv", index=False)
    val_df.to_csv(output_dir / f"{prefix}_validation.csv", index=False)
    test_df.to_csv(output_dir / f"{prefix}_test.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create stratified train/val/test CSV splits.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--prefix", choices=["email", "url"], required=True)
    parser.add_argument("--label-column", default="label")
    args = parser.parse_args()
    build_splits(args.input, args.output_dir, args.prefix, args.label_column)


if __name__ == "__main__":
    main()
