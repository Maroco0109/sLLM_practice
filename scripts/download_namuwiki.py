"""Download NamuWiki dataset in chunks and report size.

By default, only inspects size and downloads a limited number of records
to demonstrate chunked writes. Increase --max-records to fetch more.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from huggingface_hub import HfApi
from datasets import load_dataset, IterableDataset, load_dataset_builder


def human_bytes(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    if n <= 0:
        return "0 B"
    exp = min(int(math.log(n, 1024)), len(units) - 1)
    return f"{n / 1024**exp:.2f} {units[exp]}"


def estimate_repo_size(repo_id: str) -> int:
    api = HfApi()
    info = api.repo_info(repo_id=repo_id, repo_type="dataset")
    total = 0
    for s in info.siblings:
        if s.size is not None:
            total += s.size
    if total > 0:
        return total
    # Fallback to datasets builder metadata
    try:
        builder = load_dataset_builder(repo_id)
        # Prefer dataset_size; fallback to download_size
        meta_total = getattr(builder.info, "dataset_size", 0) or getattr(
            builder.info, "download_size", 0
        )
        return int(meta_total or 0)
    except Exception:
        return 0


def write_stream(ds: IterableDataset, out_dir: Path, shard_size: int, max_records: int | None) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    shard_idx = 0
    f = None
    try:
        for rec in ds:
            if max_records is not None and count >= max_records:
                break
            if f is None or (count % shard_size == 0 and count > 0):
                if f is not None:
                    f.close()
                shard_idx += 1
                f = (out_dir / f"namuwiki_{shard_idx:04d}.jsonl").open("w", encoding="utf-8")
            # Assume text-like columns exist; dump entire record as JSON
            import json

            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1
    finally:
        if f is not None:
            f.close()
    return count


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", default="heegyu/namuwiki-extracted")
    p.add_argument("--out", default="data/raw/namuwiki_stream")
    p.add_argument("--shard-size", type=int, default=100_000, help="records per JSONL shard")
    p.add_argument("--max-records", type=int, default=0, help="limit total records (0=inspect only)")
    args = p.parse_args()

    total_size = estimate_repo_size(args.repo)
    print(f"Dataset repo: {args.repo}")
    print(f"Estimated total size: {human_bytes(total_size)} ({total_size} bytes)")

    if args.max_records and args.max_records > 0:
        print("Starting streaming download… this may take a while.")
        ds = load_dataset(args.repo, split="train", streaming=True)  # type: ignore
        wrote = write_stream(ds, Path(args.out), args.shard_size, args.max_records)
        print(f"Wrote {wrote} records into shards under {args.out}")
    else:
        print("Inspection only (pass --max-records to download by chunk).")


if __name__ == "__main__":
    main()
