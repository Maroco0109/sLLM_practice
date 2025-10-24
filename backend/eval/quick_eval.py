"""Quick evaluation script placeholder as referenced in README.

KO: README에서 언급된 빠른 평가 스크립트의 자리표시자입니다.
- 입력 인자: `--model` (모델/체크포인트 경로), `--prompts` (프롬프트 JSONL 경로)
- 현재 동작: 경로를 출력하여 실행 경로를 확인합니다.
- 추후 계획: Transformers 또는 서빙된 엔드포인트를 통해 응답을 생성하고,
  기본적인 지표(응답 길이, 성공률 등)를 로깅하도록 확장합니다.
"""

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
