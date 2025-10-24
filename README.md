# sLLM-KR: Qwen2.5 기반 한국어 위키 파인튜닝 & 웹 챗봇

한국어 위키백과와 나무위키 텍스트로 Qwen2.5 계열(sLLM 사이즈 권장)을 SFT/QLoRA로 파인튜닝하고, FastAPI 백엔드 + (예: Next.js/React) 프론트엔드로 간단한 QA 챗봇을 제공합니다. 학습 파이프라인(데이터 수집 → 전처리 → 학습 → 검증)과 배포(vLLM or Transformers)까지 포함합니다.
Qwen2.5 최신 베이스/인스트럭트 모델은 Hugging Face에서 공개되어 있으며(0.5B~72B), 많은 변형이 Apache-2.0 라이선스입니다. 일부 변형은 Qwen 전용/비상업 라이선스가 적용되므로 모델별 라이선스를 반드시 확인하세요. ([Hugging Face][1])

> ⚠️ 데이터/라이선스 주의
>
> * **한국어 위키백과**: 덤프는 Wikimedia에서 공식 제공됩니다. ([Wikimedia Downloads][2])
> * **나무위키**: 공개된 덤프/데이터셋은 **CC BY-NC-SA 2.0**(비영리)입니다. 상업 목적 사용 불가이며 동일조건변경허락(ShareAlike) 조항을 준수해야 합니다. 프로젝트 목적에 맞게 사용 범위를 확인하세요. ([Hugging Face][3])

---

## 1) 아키텍처 개요

```
[데이터 소스]
  ├─ 한국어 위키백과 덤프 (XML)
  └─ 나무위키 코퍼스 (CC BY-NC-SA 2.0)

[전처리]
  ├─ WikiExtractor로 텍스트 추출/정제
  └─ QA 형태 또는 지시형(SFT) 포맷 변환(JSONL)

[학습(TRL)]
  ├─ QLoRA/LoRA (bitsandbytes 4/8bit)
  ├─ SFTTrainer로 감독학습
  └─ (선택) DPO 등 후처리

[평가/검증]
  ├─ 샘플 질의 응답 정확도/유창성
  └─ 한국어 도메인 스팟체크

[서빙]
  ├─ vLLM(OpenAI-호환 서버) 또는 Transformers + FastAPI
  └─ 프론트엔드(React/Next.js) 챗 UI
```

* SFT/QLoRA에는 Hugging Face **TRL**과 **Transformers**를 사용합니다. ([Hugging Face][4])
* 고성능 서빙은 **vLLM** OpenAI-호환 서버를 권장합니다(빠른 토크나이저/KV 캐시 관리). ([VLLM Docs][5])

---

## 2) 기술 스택

* **모델**: Qwen2.5 (예: `Qwen/Qwen2.5-0.5B`, `Qwen/Qwen2.5-7B[-Instruct]`) ([Hugging Face][6])
* **학습 라이브러리**: PyTorch, Transformers, TRL, PEFT, bitsandbytes(QLoRA) ([GitHub][7])
* **데이터 전처리**: WikiExtractor (위키 XML → 평문) ([GitHub][8])
* **서빙**: vLLM(OpenAI 호환 서버) 또는 FastAPI + Transformers ([VLLM Docs][9])
* **프론트엔드**: Next.js/React(선호 스택 사용)

---

## 3) 리포지토리 구조

```
.
├─ backend/
│  ├─ api/                # FastAPI 라우트 (chat, health)
│  ├─ serve_vllm/         # vLLM 실행 스크립트/템플릿
│  ├─ model/              # 로더/토크나이저/생성 설정
│  ├─ eval/               # 간단한 평가 스크립트
│  └─ requirements.txt
├─ frontend/
│  ├─ app/                # Next.js pages/app
│  └─ package.json
├─ data/
│  ├─ raw/                # 원본 덤프 (kowiki XML, namuwiki parquet/txt)
│  └─ processed/          # 정제 텍스트, SFT JSONL
├─ training/
│  ├─ configs/            # YAML(모델/LoRA/하이퍼파라미터)
│  ├─ preprocess.py       # WikiExtractor 호출 + 정제
│  ├─ build_sft.py        # 지시형/QA 포맷으로 변환
│  ├─ train_sft.py        # TRL SFTTrainer(QLoRA)
│  └─ merge_lora.py       # LoRA 가중치 병합(선택)
├─ scripts/
│  ├─ download_kowiki.sh
│  └─ download_namuwiki.sh
├─ docker/
│  ├─ Dockerfile.train
│  ├─ Dockerfile.serve
│  └─ compose.yaml
└─ README.md
```

---

## 4) 빠른 시작

### 4.1 환경

```bash
# 파이썬/가상환경 준비 후
pip install -r backend/requirements.txt
pip install -r training/requirements.txt
```

* TRL 기반 QLoRA 예제는 `transformers`, `datasets`, `accelerate`, `bitsandbytes`, `trl`, `peft`를 사용합니다. (PyTorch 2.4+ 권장) ([Hugging Face][4])

### 4.2 데이터 다운로드

#### (A) 한국어 위키백과

```bash
# 최신 kowiki 덤프 경로 확인
# https://dumps.wikimedia.org/kowiki/  에서 YYYYMMDD 선택 → 2025.10.24 기준 20251020 사용
mkdir -p data/raw && cd data/raw
wget https://dumps.wikimedia.org/kowiki/20251020/kowiki-20251020-pages-articles.xml.bz2
```

PowerShell (Windows, recommended on this repo):

```powershell
# Auto-detect latest date, show size, and resume if interrupted
pwsh -NoLogo -File scripts/download_kowiki.ps1 -Project kowiki -OutDir data/raw
# Or run via PowerShell in the repo root
# .\scripts\download_kowiki.ps1 -Project kowiki -OutDir data\raw
```

* Wikimedia는 정기적으로 각 언어 위키 덤프를 제공합니다. ([Wikimedia Downloads][2])

#### (B) 나무위키

* 예시: Hugging Face에 커뮤니티가 업로드한 나무위키 추출본을 사용할 수 있으나 **CC BY-NC-SA 2.0 (비영리)** 입니다. 상업/배포 조건을 반드시 확인하세요.
  (예: `heegyu/namuwiki-extracted` 등) ([Hugging Face][3])

```bash
# 예시 - datasets 라이브러리로 로컬 캐시 다운로드
python - << 'PY'
from datasets import load_dataset
ds = load_dataset("heegyu/namuwiki-extracted")
print(ds, ds['train'][0])
PY
```

> 💡 Kaggle/GitHub에도 파생 데이터가 있으나, **원본 라이선스/출처/사용조건을 재확인** 하세요. ([Kaggle][10])

### 4.3 전처리 (WikiExtractor)

```bash
# WikiExtractor 설치
pip install wikiextractor

# 위키백과 XML → 평문 JSON/텍스트
python -m wikiextractor \
  --json \
  --processes 8 \
  --output data/processed/kowiki_json \
  data/raw/kowiki-2025xxxx-pages-articles.xml.bz2
```

* WikiExtractor는 위키 덤프에서 본문 텍스트를 추출/정제하는 표준 도구입니다. ([GitHub][8])

### 4.4 SFT 데이터 빌드(지시형/QA 포맷)

```bash
python training/build_sft.py \
  --sources data/processed/kowiki_json \
  --namu_parquet data/raw/namuwiki.parquet \
  --out data/processed/sft_train.jsonl \
  --schema instruct  # instruct | qa
```

* 스키마 예시(instruct):

```json
{"messages": [{"role":"system","content":"너는 한국어 도우미야."},
              {"role":"user","content":"달걀 삶는 법 알려줘."}],
 "response": "끓는 물에 9~12분..."}
```

---

## 5) 학습(QLoRA with TRL)

### 5.1 설정(YAML)

`training/configs/qwen2p5_0_5b_qlora.yaml` (예시)

```yaml
model_name: Qwen/Qwen2.5-0.5B
load_in_4bit: true
bnb_4bit_compute_dtype: bfloat16
lora:
  r: 16
  alpha: 32
  dropout: 0.05
  target_modules:
    - q_proj
    - v_proj
data:
  train_file: data/processed/sft_train.jsonl
  max_seq_length: 2048
training:
  per_device_train_batch_size: 4
  gradient_accumulation_steps: 4
  learning_rate: 2.0e-4
  num_train_epochs: 2
  logging_steps: 10
  save_steps: 1000
  output_dir: outputs/qwen2p5_0_5b_qlora
```

### 5.2 실행

```bash
python training/train_sft.py --config training/configs/qwen2p5_0_5b_qlora.yaml
```

* TRL의 `SFTTrainer` + PEFT(LoRA/QLoRA)로 메모리 효율적 미세조정이 가능합니다. ([Hugging Face][4])
* QLoRA(4/8bit, bitsandbytes)로 VRAM을 크게 절약합니다. ([Philschmid][11])

### 5.3 (선택) LoRA 병합

```bash
python training/merge_lora.py \
  --base Qwen/Qwen2.5-0.5B \
  --lora outputs/qwen2p5_0_5b_qlora \
  --out outputs/qwen2p5_0_5b_merged
```

---

## 6) 검증 & 스팟체크

```bash
python backend/eval/quick_eval.py \
  --model outputs/qwen2p5_0_5b_qlora \
  --prompts samples/ko_eval_prompts.jsonl
```

* 간단한 정밀도/일관성/사실성 점검과 금칙어/라이선스 준수 여부를 확인합니다.

---

## 7) 서빙(두 가지 옵션)

### 옵션 A) **vLLM** OpenAI 호환 서버

```bash
# vLLM 서버 실행 (예: 병합된 가중치 사용)
python -m vllm.entrypoints.openai.api_server \
  --model outputs/qwen2p5_0_5b_merged \
  --port 8000
```

* vLLM은 OpenAI Chat/Completions 호환 REST API를 제공합니다. 프론트/백엔드에서 동일한 프로토콜로 쉽게 붙일 수 있습니다. ([VLLM Docs][9])

### 옵션 B) **FastAPI + Transformers** 경량 서버

```bash
uvicorn backend.api.app:app --host 0.0.0.0 --port 8000
```

* 참고: FastAPI와 vLLM/Transformers 조합 튜토리얼들이 다수 존재합니다(성능/운영 편의는 vLLM 권장). ([Runpod][12])

---

## 8) 프론트엔드(예: Next.js)

1. `.env.local`에 백엔드 엔드포인트(URL, 키 등) 설정
2. 채팅 UI 컴포넌트에서 `/api/chat` 호출 (스트리밍/에러 표시/리트라이)

```bash
cd frontend
pnpm install
pnpm dev
```

---

## 9) Docker & 배포

* `docker/compose.yaml`에 `train`, `serve`, `frontend` 서비스 정의
* GPU 서버에서는 `--gpus all`, vLLM 컨테이너에 모델 볼륨 마운트

```bash
docker compose -f docker/compose.yaml up -d
```

---

## 10) 라이선스 & 컴플라이언스 체크리스트

* **Qwen2.5**: 다수 변형은 Apache-2.0이지만, 일부(특히 VL/특정 사이즈)는 **Qwen 전용 라이선스(비상업/별도 허가)** 입니다. 사용 모델의 **Hugging Face 카드의 LICENSE 파일**을 반드시 확인하세요. ([Qwen][13])
* **나무위키 데이터**: **CC BY-NC-SA 2.0**. 상업적 사용 불가, 동일조건변경허락 필요. 코드/가중치/데이터 배포 정책에 영향. ([Hugging Face][3])
* **위키백과**: 덤프는 자유 사용 가능하나, 문서별 라이선스(Creative Commons Attribution-ShareAlike 3.0/4.0)와 출처 표기를 준수하세요. ([위키백과][14])

---

## 11) 벤치마크/운영 팁

* 작은 모델(0.5B~3B)은 학습/서빙 비용이 낮고 빠릅니다. 7B는 품질/리소스 균형. (모델 라인업은 Qwen2.5 허브에서 확인) ([Hugging Face][1])
* 프롬프트 템플릿은 학습과 서빙에서 일치시켜 **포맷 드리프트**를 방지하세요(예: `<|im_start|>system` 스타일 등, 모델 카드 참조). ([Hugging Face][15])
* 대규모 트래픽은 vLLM + 로드밸런싱(헬스체크/워커) 구성을 고려하세요. ([docs.runpod.io][16])

---

## 12) 참고 자료

* **Qwen2.5 모델 허브/블로그**: 개요·라인업·라이선스 요약 ([Hugging Face][1])
* **한국어 위키백과 덤프**: 최신 kowiki 경로 ([Wikimedia Downloads][2])
* **WikiExtractor**: 위키 덤프 텍스트 추출 도구 ([GitHub][8])
* **나무위키 데이터셋 예시**: Hugging Face(라이선스: CC BY-NC-SA 2.0) ([Hugging Face][3])
* **TRL(QLoRA/SFT)**: Hugging Face TRL 문서/가이드 ([Hugging Face][4])
* **vLLM**: 퀵스타트/오픈AI 호환 서버 ([VLLM Docs][5])

---

## 13) 로드맵(옵션)

* [ ] 평가 세트 구성(위키 기반 추출 Q/A, 도메인 지식 질문)
* [ ] DPO/GRPO 등 선호학습 실험 ([Hugging Face][4])
* [ ] 지식 최신화(정기 덤프 재학습 또는 RAG 혼합)
* [ ] 모니터링(응답 길이, 지연시간, 금칙어, 안전성)

---

## 14) 기여

PR/이슈 환영합니다. 데이터/모델 라이선스 위반 가능성이 있는 변경은 반드시 논의해주세요.

---

### 부록 A. 최소 예제: TRL SFT(QLoRA)

```python
# training/train_sft.py (개념예시)
from trl import SFTTrainer
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from peft import LoraConfig, get_peft_model
import bitsandbytes as bnb
import json

model_name = "Qwen/Qwen2.5-0.5B"
tok = AutoTokenizer.from_pretrained(model_name, use_fast=True)
model = AutoModelForCausalLM.from_pretrained(
    model_name, load_in_4bit=True, bnb_4bit_compute_dtype="bfloat16"
)

peft_cfg = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules=["q_proj","v_proj"])
model = get_peft_model(model, peft_cfg)

train_data = [json.loads(l) for l in open("data/processed/sft_train.jsonl")]
args = TrainingArguments(
    per_device_train_batch_size=4, gradient_accumulation_steps=4,
    learning_rate=2e-4, num_train_epochs=2, logging_steps=10,
    output_dir="outputs/qwen2p5_0_5b_qlora"
)
trainer = SFTTrainer(model=model, tokenizer=tok, train_dataset=train_data, args=args)
trainer.train()
```

> TRL/QLoRA 참조. 실제 구현은 체크포인트/로깅/혼합정밀/감속 스케줄 등 옵션을 추가하세요. ([Hugging Face][4])

---

[1]: https://huggingface.co/Qwen/Qwen2.5-7B?utm_source=chatgpt.com "Qwen/Qwen2.5-7B"
[2]: https://dumps.wikimedia.org/kowiki/?utm_source=chatgpt.com "Index of /kowiki/"
[3]: https://huggingface.co/datasets/heegyu/namuwiki-extracted?utm_source=chatgpt.com "heegyu/namuwiki-extracted · Datasets at Hugging Face"
[4]: https://huggingface.co/docs/trl/en/index?utm_source=chatgpt.com "TRL - Transformer Reinforcement Learning"
[5]: https://docs.vllm.ai/en/stable/getting_started/quickstart.html?utm_source=chatgpt.com "Quickstart - vLLM"
[6]: https://huggingface.co/Qwen/Qwen2.5-0.5B?utm_source=chatgpt.com "Qwen/Qwen2.5-0.5B"
[7]: https://github.com/huggingface/transformers?utm_source=chatgpt.com "Transformers: the model-definition framework for state-of- ..."
[8]: https://github.com/attardi/wikiextractor?utm_source=chatgpt.com "attardi/wikiextractor: A tool for extracting plain text from ..."
[9]: https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html?utm_source=chatgpt.com "OpenAI-Compatible Server - vLLM"
[10]: https://www.kaggle.com/datasets/brainer3220/namu-wiki/data?utm_source=chatgpt.com "Namu Wiki"
[11]: https://www.philschmid.de/fine-tune-llms-in-2025?utm_source=chatgpt.com "How to fine-tune open LLMs in 2025 with Hugging Face"
[12]: https://www.runpod.io/articles/guides/serving-phi-2-cloud-gpu-vllm-fastapi?utm_source=chatgpt.com "How to Serve Phi-2 on a Cloud GPU with vLLM and FastAPI"
[13]: https://qwenlm.github.io/blog/qwen2.5/?utm_source=chatgpt.com "Qwen2.5: A Party of Foundation Models! | Qwen"
[14]: https://en.wikipedia.org/wiki/Wikipedia%3ADatabase_download?utm_source=chatgpt.com "Wikipedia:Database download"
[15]: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct?utm_source=chatgpt.com "Qwen/Qwen2.5-7B-Instruct"
[16]: https://docs.runpod.io/serverless/load-balancing/vllm-worker?utm_source=chatgpt.com "Build a load balancing vLLM endpoint"

## Windows PowerShell Commands

PowerShell에서는 Bash의 `\` 줄바꿈 이어쓰기가 동작하지 않습니다. 아래와 같이 한 줄 명령으로 실행하세요.

- 전처리(WikiExtractor JSON):
  - `python training/preprocess.py --input "data/raw/kowiki-YYYYMMDD-pages-articles.xml.bz2" --output "data/processed/kowiki_json" --processes 8`
- SFT JSONL 빌드(instruct 스키마):
  - `python training/build_sft.py --sources "data/processed/kowiki_json" --out "data/processed/sft_train.jsonl" --schema instruct`
- 나무위키 Parquet 사용 시:
  - `python training/build_sft.py --sources "data/processed/kowiki_json" --namu_parquet "data/raw/namuwiki.parquet" --out "data/processed/sft_train.jsonl" --schema instruct`
- 나무위키 스트리밍 샤드 사용 시:
  - `python training/build_sft.py --namu_stream_dir "data/raw/namuwiki_stream" --out "data/processed/sft_train.jsonl" --schema instruct`
