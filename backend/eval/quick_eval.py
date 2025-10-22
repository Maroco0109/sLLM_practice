"""Quick evaluation script placeholder as referenced in README."""

from __future__ import annotations

from pathlib import Path


def main(model_path: str, prompts_path: str) -> None:
    """Log provided paths so contributors can wire in evaluation later."""
    print(f"Model path: {Path(model_path).resolve()}")
    print(f"Prompts path: {Path(prompts_path).resolve()}")
    print("TODO: implement evaluation pipeline.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run quick offline evaluation.")
    parser.add_argument("--model", required=True, help="Path to fine-tuned model")
    parser.add_argument("--prompts", required=True, help="JSONL file with prompts")
    args = parser.parse_args()
    main(args.model, args.prompts)
