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
import bz2
import json
import os
import re
import shutil
import shutil as _shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterator, Tuple


def run_wikiextractor(
    input_xml_bz2: Path,
    output_dir: Path,
    processes: int | None = None,
    json_output: bool = True,
    overwrite: bool = False,
    prefer_builtin: bool = False,
    max_pages: int = 0,
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

    if prefer_builtin:
        print("Skipping external WikiExtractor (prefer_builtin=True).")
        run_builtin_extractor(
            input_xml_bz2=input_xml_bz2,
            output_dir=output_dir,
            json_output=json_output,
            max_pages=max_pages,
        )
        return

    # Prefer console script if available; otherwise fall back to module forms.
    cmd: list[str] | None = None
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
    if cmd is None:
        print("wikiextractor CLI not available. Falling back to builtin parser.")
        run_builtin_extractor(
            input_xml_bz2=input_xml_bz2,
            output_dir=output_dir,
            json_output=json_output,
            max_pages=max_pages,
        )
        return

    if json_output:
        cmd.append("--json")

    cmd.append(str(input_xml_bz2))

    print("Running:", " ".join(cmd))
    # Run and capture output so we can surface clear errors and retry.
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        return

    try:
        print(f"WikiExtractor failed with exit code {proc.returncode}")
        if proc.stderr:
            stderr_lines = proc.stderr.splitlines()
            tail = "\n".join(stderr_lines[-80:])
            print("--- stderr (last 80 lines) ---\n" + tail)
    except Exception:
        pass

    # Attempt fallback invocation when console wrapper failed.
    fallback_cmd: list[str] | None = None
    if cmd and cmd[0] != sys.executable:
        try:
            import importlib.util as _ilu

            has_main = _ilu.find_spec("wikiextractor.__main__") is not None
            has_sub = _ilu.find_spec("wikiextractor.WikiExtractor") is not None
        except Exception:
            has_main = False
            has_sub = True

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
        if proc2.returncode == 0:
            return
        try:
            print(f"Fallback failed with exit code {proc2.returncode}")
            if proc2.stderr:
                stderr_lines = proc2.stderr.splitlines()
                tail = "\n".join(stderr_lines[-80:])
                print("--- fallback stderr (last 80 lines) ---\n" + tail)
        except Exception:
            pass

    print("Falling back to builtin XML parser.")
    run_builtin_extractor(
        input_xml_bz2=input_xml_bz2,
        output_dir=output_dir,
        json_output=json_output,
        max_pages=max_pages,
    )


def strip_markup(text: str) -> str:
    """Very lightweight Wiki markup stripper (not perfect, but SFT-friendly)."""
    if not text:
        return ""
    txt = text
    txt = txt.replace("\r", "")
    txt = re.sub(r"<!--.*?-->", " ", txt, flags=re.DOTALL)
    txt = re.sub(r"<ref[^>]*>.*?</ref>", " ", txt, flags=re.IGNORECASE | re.DOTALL)
    txt = re.sub(r"<[^>]+>", " ", txt)
    # Remove file/image links early
    txt = re.sub(r"\[\[(?:파일|File):[^\]]+\]\]", " ", txt, flags=re.IGNORECASE)
    # Iteratively strip templates to handle limited nesting
    for _ in range(5):
        new_txt = re.sub(r"\{\{[^{}]*\}\}", " ", txt)
        if new_txt == txt:
            break
        txt = new_txt
    txt = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", txt)
    txt = re.sub(r"\[http[^\s\]]+\s([^\]]+)\]", r"\1", txt)
    txt = re.sub(r"'{2,}", "", txt)
    txt = re.sub(r"==+\s*(.*?)\s*==+", r"\n\1\n", txt)
    txt = txt.replace("&quot;", '"').replace("&amp;", "&")
    # Normalize whitespace but keep paragraph breaks
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n{2,}", "\n\n", txt)
    txt = re.sub(r" ?\n ?", "\n", txt)
    txt = re.sub(r"\s+\Z", "", txt)
    return txt.strip()


def iter_wiki_pages(dump_path: Path) -> Iterator[Tuple[str, str]]:
    """Yield (title, text) from a Wikipedia XML dump."""
    with bz2.open(dump_path, "rb") as f:
        context = ET.iterparse(f, events=("end",))
        for event, elem in context:
            if not elem.tag.endswith("page"):
                continue
            ns_elem = elem.find("./{*}ns")
            if ns_elem is not None and ns_elem.text != "0":
                elem.clear()
                continue
            title_elem = elem.find("./{*}title")
            revision_elem = elem.find("./{*}revision")
            text_elem = None
            if revision_elem is not None:
                text_elem = revision_elem.find("./{*}text")
            title = title_elem.text if title_elem is not None else ""
            text = text_elem.text if text_elem is not None else ""
            yield title or "", text or ""
            elem.clear()


def run_builtin_extractor(
    input_xml_bz2: Path,
    output_dir: Path,
    json_output: bool,
    max_pages: int = 0,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / ("wiki_00.jsonl" if json_output else "wiki_00.txt")
    total = 0
    with out_file.open("w", encoding="utf-8") as out:
        for title, raw in iter_wiki_pages(input_xml_bz2):
            text = strip_markup(raw)
            if not text:
                if max_pages and total >= max_pages:
                    break
                continue
            total += 1
            if json_output:
                out.write(
                    json.dumps(
                        {"title": title, "text": text, "source": "kowiki"},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            else:
                out.write(f"<doc title=\"{title}\">\n{text}\n</doc>\n")
            if max_pages and total >= max_pages:
                break
            if total % 10000 == 0:
                print(f"[builtin] Processed {total} articles…")
    print(f"[builtin] Wrote {total} articles to {out_file}")


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
    p.add_argument(
        "--prefer-builtin",
        action="store_true",
        help="Skip external wikiextractor binary and use builtin parser directly",
    )
    p.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Limit number of articles processed (0 = all)",
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
        prefer_builtin=args.prefer_builtin,
        max_pages=args.max_pages,
    )


if __name__ == "__main__":
    main()
