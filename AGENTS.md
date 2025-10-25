# Repository Guidelines

## Project Structure & Module Organization
- `backend/` – FastAPI app (`backend/api/app.py`), evaluation scripts (`backend/eval/`), and tests (`backend/tests/`).
- `training/` – Data and model pipeline: `preprocess.py`, `build_sft.py`, `train_sft.py`, and configs under `training/configs/`.
- `frontend/` – Next.js client in `frontend/app/`.
- `data/` – `raw/` for dumps, `processed/` for WikiExtractor output and SFT JSONL (`data/processed/sft_train.jsonl`).
- `scripts/` – Download utilities (e.g., `download_kowiki.sh`, `download_namuwiki.py`).

## Build, Test, and Development Commands
- Install deps: `pip install -r backend/requirements.txt` and `pip install -r training/requirements.txt`.
- Preprocess wiki dump: `python training/preprocess.py --input data/raw/kowiki-YYYYMMDD-pages-articles.xml.bz2 --output data/processed/kowiki_json --processes 8`.
- Build SFT dataset: `python training/build_sft.py --sources data/processed/kowiki_json --out data/processed/sft_train.jsonl --schema instruct`.
- Train QLoRA: `python training/train_sft.py --config training/configs/qwen2p5_0_5b_qlora.yaml`.
- Merge LoRA weights: `python training/merge_lora.py --base Qwen/Qwen2.5-0.5B --lora outputs/<run> --out outputs/<merged>`.
- Backend quick eval: `python backend/eval/quick_eval.py --model outputs/<run> --prompts samples/ko_eval_prompts.jsonl`.
- Run API locally: `uvicorn backend.api.app:app --host 0.0.0.0 --port 8000`. Frontend: `cd frontend && pnpm install && pnpm dev`.

## Coding Style & Naming Conventions
- Python: PEP8, 4-space indent, prefer type hints; keep modules ASCII unless data requires UTF-8.
- Frontend: follow Next.js defaults, functional React components, camelCase for hooks/state, PascalCase for components.
- Config and dataset paths should remain lowercase with underscores (`sft_train.jsonl`, `qwen2p5_0_5b_qlora.yaml`).

## Testing Guidelines
- Python tests use `pytest`; run `pytest backend/tests -q` for backend health checks.
- Add regression tests beside related modules (`backend/tests/test_*.py`).
- For data scripts, provide smoke tests via `--max-records` or `--max-pages` to keep runtime manageable.

## Commit & Pull Request Guidelines
- Write imperative, scoped commit messages (e.g., `feat: add builtin wiki extractor fallback`).
- PRs should summarize intent, list key changes, and mention related issues.
- Include screenshots or sample CLI output when altering UI or pipelines.
- Ensure CI commands (`pytest`, dataset builders, type checks if applicable) pass before requesting review.

## Security & Configuration Tips
- Store large dumps under `data/raw/`; never commit raw dumps or checkpoints.
- `.env`, API keys, or Hugging Face tokens belong in local environment files, not Git.
- When preprocessing on restricted networks, use `training/preprocess.py --prefer-builtin` to avoid external downloads.
