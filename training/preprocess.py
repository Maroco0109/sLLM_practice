"""Data preprocessing utilities.

Implements README 4.3: Run WikiExtractor on a downloaded Wikipedia
XML dump to generate cleaned JSON/text shards.

Example:
    python training/preprocess.py \
      --input data/raw/kowiki-2025xxxx-pages-articles.xml.bz2 \
      --output data/processed/kowiki_json \
      --processes 8

Notes:
    - Requires `wikiextractor` to be installed.
    - This is a thin wrapper that shells out to
      `python -m wikiextractor.WikiExtractor` to avoid relying on
      internal, non‑stable APIs.
"""

# KO: 위키데이터 전처리 유틸리티입니다. README 4.3을 구현하여, 다운로드한
# Wikipedia XML 덤프에 대해 WikiExtractor를 실행하고 정제된 JSON/텍스트 샤드를
# 생성합니다. 주요 인자: --input, --output, --processes, --no-json, --overwrite
# 예시:
#   python training/preprocess.py --input data/raw/kowiki-YYYYMMDD-pages-articles.xml.bz2 \
#     --output data/processed/kowiki_json --processes 8

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_wikiextractor(
    input_xml_bz2: Path,
    output_dir: Path,
    processes: int | None = None,
    json_output: bool = True,
    overwrite: bool = False,
) -> None:
    """Run WikiExtractor to process a Wikipedia XML dump.

    Args:
        input_xml_bz2: Path to the `*pages-articles.xml.bz2` file.
        output_dir: Directory where extracted shards will be written.
        processes: Number of worker processes. Defaults to os.cpu_count().
        json_output: Emit JSON lines instead of plain text when True.
        overwrite: If True, remove existing output directory first.
    """
    if not input_xml_bz2.exists():
        raise FileNotFoundError(f"Input dump not found: {input_xml_bz2}")

    if output_dir.exists():
        if overwrite:
            shutil.rmtree(output_dir)
        else:
            # Ensure directory exists but do not remove; WikiExtractor will append.
            output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir.mkdir(parents=True, exist_ok=True)

    procs = processes or (os.cpu_count() or 1)

    cmd = [
        sys.executable,
        "-m",
        "wikiextractor.WikiExtractor",
        "--processes",
        str(procs),
        "--output",
        str(output_dir),
    ]
    if json_output:
        cmd.append("--json")

    cmd.append(str(input_xml_bz2))

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Preprocess datasets (WikiExtractor wrapper for README 4.3)",
    )
    p.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to kowiki '*pages-articles.xml.bz2' dump",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/kowiki_json"),
        help="Output directory for extracted shards (default: data/processed/kowiki_json)",
    )
    p.add_argument(
        "--processes",
        type=int,
        default=None,
        help="Number of worker processes (default: cpu_count)",
    )
    p.add_argument(
        "--no-json",
        action="store_true",
        help="Emit plain text instead of JSON lines",
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Remove existing output directory before extraction",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_argparser().parse_args(argv)
    run_wikiextractor(
        input_xml_bz2=args.input,
        output_dir=args.output,
        processes=args.processes,
        json_output=not args.no_json,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
