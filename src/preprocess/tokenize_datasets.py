from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from datasets import Dataset, DatasetDict
from transformers import AutoTokenizer


def tokenize_data(prefix: str, text_col: str) -> None:
    print(f"Preparing to tokenize {prefix.upper()} dataset...")
    data_dir = Path("data/processed")

    # Load the CSV splits
    train_path = data_dir / f"{prefix}_train.csv"
    val_path = data_dir / f"{prefix}_validation.csv"
    test_path = data_dir / f"{prefix}_test.csv"

    if not train_path.exists():
        print(f"Splits for {prefix} not found at {train_path}.")
        return

    # Create Hugging Face datasets directly from pandas DataFrames
    dataset = DatasetDict(
        {
            "train": Dataset.from_pandas(pd.read_csv(train_path).dropna()),
            "validation": Dataset.from_pandas(pd.read_csv(val_path).dropna()),
            "test": Dataset.from_pandas(pd.read_csv(test_path).dropna()),
        }
    )

    # Initialize the official RoBERTa tokenizer using the HF token if available
    hf_token = os.environ.get("HF_TOKEN")
    tokenizer = AutoTokenizer.from_pretrained("roberta-base", token=hf_token)

    # Set max length based on the task (512 for email, 128 for URL)
    max_len = 128 if prefix == "url" else 512

    # Define the tokenization function
    def tokenize_function(examples):
        return tokenizer(
            examples[text_col], padding="max_length", truncation=True, max_length=max_len
        )

    print(f"Applying RoBERTa tokenizer to {prefix} splits...")
    # Apply tokenization using batched=True for massive speed improvements
    tokenized_dataset = dataset.map(tokenize_function, batched=True)

    # Set the format to PyTorch tensors so the model can read it directly
    tokenized_dataset.set_format(type="torch", columns=["input_ids", "attention_mask", "label"])

    # Save to disk
    out_dir = Path(f"data/tokenized/{prefix}")
    tokenized_dataset.save_to_disk(out_dir)
    print(f"Successfully tokenized and saved {prefix} dataset to {out_dir}\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    # Tokenize Emails (the text column is named 'text')
    tokenize_data(prefix="email", text_col="text")

    # Tokenize URLs (the text column is named 'url')
    tokenize_data(prefix="url", text_col="url")
