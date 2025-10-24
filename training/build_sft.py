"""Build SFT-ready JSONL from Wikipedia/NamuWiki sources.

Implements README 4.4:

Example:
    python training/build_sft.py \
      --sources data/processed/kowiki_json \
      --namu_parquet data/raw/namuwiki.parquet \
      --out data/processed/sft_train.jsonl \
      --schema instruct  # instruct | qa

Outputs JSONL in one of two schemas:
  - instruct: {"messages": [{"role":"system","content":...},
                              {"role":"user","content":...}],
               "response": "..."}
  - qa:       {"question": "...", "answer": "..."}
"""

# KO: WikiExtractor 결과 및 나무위키(Parquet/스트리밍)를 SFT 학습용 JSONL로
# 변환합니다. 스키마는 두 가지(`instruct`, `qa`)를 지원합니다.
# - instruct: messages(시스템/사용자 프롬프트) + response 형태
# - qa: question + answer 형태
# 입력 옵션: --sources(여러 디렉터리), --namu_parquet, --namu_stream_dir
# 출력 옵션: --out, 레코드 제한: --max-records

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Iterable


# --------------------
# Data model helpers
# --------------------

@dataclass
class Article:
    title: str
    text: str
    source: str


def _read_jsonl(path: Path) -> Generator[dict, None, None]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def iter_wikiextractor_dir(root: Path) -> Iterable[Article]:
    exts = {".json", ".jsonl"}
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            for rec in _read_jsonl(p):
                title = (rec.get("title") or "").strip()
                text = (rec.get("text") or "").strip()
                if not text:
                    continue
                yield Article(title=title or "", text=text, source="kowiki")


def iter_namuwiki_parquet(parquet_path: Path) -> Iterable[Article]:
    try:
        from datasets import load_dataset  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Loading parquet requires 'datasets' (and likely 'pyarrow').\n"
            "Install optional deps: pip install datasets pyarrow"
        ) from e

    ds = load_dataset("parquet", data_files=str(parquet_path))
    split = ds.get("train") or next(iter(ds.values()))
    for rec in split:
        title = (rec.get("title") or rec.get("doc_title") or rec.get("name") or "").strip()
        text = (
            rec.get("text")
            or rec.get("document")
            or rec.get("content")
            or rec.get("body")
            or ""
        )
        text = str(text).strip()
        if not text:
            continue
        yield Article(title=title or "", text=text, source="namuwiki")


def iter_namuwiki_stream_dir(root: Path) -> Iterable[Article]:
    for p in sorted(root.glob("*.jsonl")):
        for rec in _read_jsonl(p):
            title = (rec.get("title") or rec.get("doc_title") or rec.get("name") or "").strip()
            text = (
                rec.get("text")
                or rec.get("document")
                or rec.get("content")
                or rec.get("body")
                or ""
            )
            text = str(text).strip()
            if not text:
                continue
            yield Article(title=title or "", text=text, source="namuwiki")


# --------------------
# Schema conversion
# --------------------

def first_paragraph(text: str, max_chars: int = 1200) -> str:
    para = text.split("\n\n", 1)[0].strip()
    if len(para) > max_chars:
        return para[: max_chars - 1].rstrip() + "…"
    return para


def to_instruct(article: Article) -> dict:
    user = (
        f"{article.title}에 대해 설명해줘." if article.title else "다음 내용을 간결히 설명해줘."
    )
    response = first_paragraph(article.text)
    return {
        "messages": [
            {"role": "system", "content": "당신은 한국어 도우미입니다."},
            {"role": "user", "content": user},
        ],
        "response": response,
        "meta": {"source": article.source, "title": article.title},
    }


def to_qa(article: Article) -> dict:
    question = f"{article.title}란 무엇인가?" if article.title else "다음에 대해 설명하라."
    answer = first_paragraph(article.text)
    return {
        "question": question,
        "answer": answer,
        "meta": {"source": article.source, "title": article.title},
    }


# --------------------
# CLI / Orchestration
# --------------------

def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Convert extracted corpora into SFT-ready JSONL (README 4.4)",
    )
    p.add_argument(
        "--sources",
        type=Path,
        nargs="+",
        required=False,
        help="Paths to WikiExtractor output directories (JSON/JSONL)",
    )
    p.add_argument(
        "--namu_parquet",
        type=Path,
        default=None,
        help="Optional path to NamuWiki parquet file",
    )
    p.add_argument(
        "--namu_stream_dir",
        type=Path,
        default=None,
        help="Optional directory of streamed NamuWiki JSONL shards",
    )
    p.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output JSONL path",
    )
    p.add_argument(
        "--schema",
        choices=["instruct", "qa"],
        default="instruct",
        help="Target schema for SFT JSONL",
    )
    p.add_argument(
        "--max-records",
        type=int,
        default=0,
        help="Optional limit on total records (0=all)",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_argparser().parse_args(argv)

    writers = {
        "instruct": to_instruct,
        "qa": to_qa,
    }
    convert = writers[args.schema]

    total = 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as out_f:
        # WikiExtractor sources
        if args.sources:
            for root in args.sources:
                root = root.resolve()
                if not root.exists():
                    continue
                for art in iter_wikiextractor_dir(root):
                    rec = convert(art)
                    out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    total += 1
                    if args.max_records and total >= args.max_records:
                        print(f"Wrote {total} records to {args.out}")
                        return

        # NamuWiki parquet
        if args.namu_parquet is not None:
            parquet = args.namu_parquet.resolve()
            if parquet.exists():
                for art in iter_namuwiki_parquet(parquet):
                    rec = convert(art)
                    out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    total += 1
                    if args.max_records and total >= args.max_records:
                        print(f"Wrote {total} records to {args.out}")
                        return

        # NamuWiki streamed JSONL shards
        if args.namu_stream_dir is not None:
            stream_dir = args.namu_stream_dir.resolve()
            if stream_dir.exists():
                for art in iter_namuwiki_stream_dir(stream_dir):
                    rec = convert(art)
                    out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    total += 1
                    if args.max_records and total >= args.max_records:
                        print(f"Wrote {total} records to {args.out}")
                        return

    print(f"Wrote {total} records to {args.out}")


if __name__ == "__main__":
    main()
