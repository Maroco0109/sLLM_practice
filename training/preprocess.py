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
import shutil as _shutil
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

    # Prefer console script if available; otherwise fall back to module forms.
    if _shutil.which("wikiextractor"):
        cmd = [
            "wikiextractor",
            "--processes",
            str(procs),
            "--output",
            str(output_dir),
        ]
    else:
        # Try top-level module (__main__) first, then legacy submodule.
        try:
            import importlib.util as _ilu

            has_main = _ilu.find_spec("wikiextractor.__main__") is not None
        except Exception:
            has_main = False

        if has_main:
            cmd = [
                sys.executable,
                "-m",
                "wikiextractor",
                "--processes",
                str(procs),
                "--output",
                str(output_dir),
            ]
        else:
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
    # Run and capture output so we can surface clear errors and retry.
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        try:
            print(f"WikiExtractor failed with exit code {proc.returncode}")
            if proc.stderr:
                stderr_lines = proc.stderr.splitlines()
                tail = "\n".join(stderr_lines[-80:])
                print("--- stderr (last 80 lines) ---\n" + tail)
        except Exception:
            pass

        # Attempt a fallback invocation if we used the console script.
        fallback_cmd: list[str] | None = None
        if cmd and cmd[0] != sys.executable:
            # Decide best module form available.
            try:
                import importlib.util as _ilu

                has_main = _ilu.find_spec("wikiextractor.__main__") is not None
                has_sub = _ilu.find_spec("wikiextractor.WikiExtractor") is not None
            except Exception:
                has_main = False
                has_sub = True  # most packages have the legacy submodule

            if has_main:
                fallback_cmd = [
                    sys.executable,
                    "-m",
                    "wikiextractor",
                    "--processes",
                    str(procs),
                    "--output",
                    str(output_dir),
                ]
            elif has_sub:
                fallback_cmd = [
                    sys.executable,
                    "-m",
                    "wikiextractor.WikiExtractor",
                    "--processes",
                    str(procs),
                    "--output",
                    str(output_dir),
                ]
            if json_output and fallback_cmd is not None:
                fallback_cmd.append("--json")
            if fallback_cmd is not None:
                fallback_cmd.append(str(input_xml_bz2))

        if fallback_cmd is not None:
            print("Retrying with:", " ".join(fallback_cmd))
            proc2 = subprocess.run(fallback_cmd, capture_output=True, text=True)
            if proc2.returncode != 0:
                try:
                    print(f"Fallback failed with exit code {proc2.returncode}")
                    if proc2.stderr:
                        stderr_lines = proc2.stderr.splitlines()
                        tail = "\n".join(stderr_lines[-80:])
                        print("--- fallback stderr (last 80 lines) ---\n" + tail)
                except Exception:
                    pass
                raise subprocess.CalledProcessError(proc2.returncode, fallback_cmd, output=proc2.stdout, stderr=proc2.stderr)
            return

        # If no fallback, propagate the original error
        raise subprocess.CalledProcessError(proc.returncode, cmd, output=proc.stdout, stderr=proc.stderr)


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
