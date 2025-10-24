"""Utility to merge LoRA adapters into a base checkpoint (placeholder).

KO: LoRA 어댑터 가중치를 기본(base) 모델 체크포인트에 병합하는 유틸리티의
자리표시자입니다. 추후 `peft`/`transformers`를 사용해 어댑터를 로드하고,
병합된 최종 가중치를 저장(export)하도록 구현될 예정입니다.
"""

from __future__ import annotations


def main() -> None:
    print("TODO: implement LoRA merge logic.")


if __name__ == "__main__":
    main()
