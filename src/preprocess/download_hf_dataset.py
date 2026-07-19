import sys
from pathlib import Path

from datasets import load_dataset

DEFAULT_DATASETS = [
    # "pleasenotagain/sanct-classify-emailspam-dataset",
    # "SchoolP/Email_Spam_Dataset",
    "Gunjand07/email-spam-dataset",
]


def main(datasets: list[str]):
    print("Getting datasets ready in data/raw/ before preprocessing...\n")

    for dataset_name in datasets:
        print(f"Downloading '{dataset_name}'...")
        try:
            # Load the train split of the dataset
            dataset = load_dataset(dataset_name, split="train")
            df = dataset.to_pandas()

            # Create a safe filename based on the dataset name
            safe_name = dataset_name.replace("/", "_")
            out_path = Path(f"data/raw/{safe_name}.csv")
            out_path.parent.mkdir(parents=True, exist_ok=True)

            # Save to CSV
            df.to_csv(out_path, index=False)
            print(f"  -> Successfully saved {len(df)} samples to {out_path}\n")

        except Exception as e:
            print(f"  -> Failed to download {dataset_name}. Error: {e}\n")

    print("All downloads complete!")


if __name__ == "__main__":
    # Run all default datasets if no argument is passed, otherwise run the single dataset requested
    targets = [sys.argv[1]] if len(sys.argv) > 1 else DEFAULT_DATASETS
    main(targets)
