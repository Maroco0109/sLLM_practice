"""SFT (Supervised Fine-Tuning) entry point placeholder.

KO: SFT 학습 파이프라인의 진입점 자리표시자입니다. 추후 `training/configs/*.yaml`
구성 파일을 읽어 TRL `SFTTrainer`와 PEFT/QLoRA 설정을 구성하고, 출력 디렉터리
및 로깅/체크포인트 경로를 반영하도록 확장될 예정입니다.
"""

from __future__ import annotations


def main() -> None:
    print("TODO: wire TRL training loop and config loading.")


if __name__ == "__main__":
    main()
