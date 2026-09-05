# Battery SOX Engine

리튬이온 배터리의 **SOC**(잔량) · **SOH**(건강도) · **SOP**(출력 가능 전력)를
등가회로모델(ECM)과 칼만필터 계열 상태추정기로 구현하는 프로젝트입니다.

> **배터리에는 잔량 센서가 없습니다.**
> 측정할 수 있는 건 단자전압·전류·온도 세 개뿐인데, 알고 싶은 건 셀 내부의
> 리튬 분포입니다. 이 간극을 물리 모델과 확률적 추정으로 메우는 것이
> 이 프로젝트의 전부입니다.

## 📖 처음 오셨나요?

**→ [docs/START_HERE.md](docs/START_HERE.md) 부터 읽어주세요.**
읽는 순서, 표기 규칙, 전체 흐름이 정리되어 있습니다.

## 이 저장소의 목적

세 가지를 동시에 겨냥합니다.

1. **개인 학습 기록** — 전기·전자공학 학부 졸업 후 세부 이론을 다시
   다지며 BMS 알고리즘 직무를 8주 커리큘럼으로 따라잡는 과정.
   **실패한 시도와 막혔던 지점을 숨기지 않고 남깁니다.**
2. **참고 자료** — 같은 방향을 준비하는 학습자가 이론적 배경부터
   구현까지 이어지는 흐름을 그대로 따라갈 수 있도록 정리합니다.
3. **포트폴리오** — 채용 지원 시 제출 가능한 수준의 완성도를 목표로 합니다.

## 로드맵

| 주차 | 내용 | 문서 | 이론 | 구현 |
|---|---|---|---|---|
| W0 | 기초 정비 (회로·제어·확률) | [W0_foundations](docs/02_theory/W0_foundations.md) | ✅ | 🔲 |
| W1 | 전기화학 → 등가회로(ECM) | [W1_electrochemistry_ecm](docs/02_theory/W1_electrochemistry_ecm.md) | ✅ | 🔲 |
| W2 | EIS와 나이퀴스트 선도 | [W2_eis](docs/02_theory/W2_eis.md) | ✅ | 🔲 |
| W3 | 파라미터 식별 (HPPC, RLS) | [W3_parameter_identification](docs/02_theory/W3_parameter_identification.md) | ✅ | 🔲 |
| W4-5 | 상태추정 (EKF/UKF) + 검증 | [W4_kalman_filter](docs/02_theory/W4_kalman_filter.md) | 🔲 | 🔲 |
| W6 | SOH (Dual EKF, ICA/DVA) | [W6_soh](docs/02_theory/W6_soh.md) | 🔲 | 🔲 |
| W7 | SOP (제약 하 최적화) | [W7_sop](docs/02_theory/W7_sop.md) | 🔲 | 🔲 |
| W8 | 제품화 (임베디드, 기능안전) | [W8_productionization](docs/02_theory/W8_productionization.md) | 🔲 | 🔲 |

## 데이터

McMaster University(캐나다)에서 공개한 **LG 18650HG2** 및
**Samsung INR21700 30T** 데이터셋을 사용합니다. 각 데이터셋의 구조,
시험 블록별 목적, HPPC 포함 여부에 대한 주의사항은
**[data/README.md](data/README.md)** 를 참고하세요.

## 저장소 구조

```
battery-sox-engine/
├── docs/
│   ├── START_HERE.md           # 👈 여기부터
│   ├── 00_learning_log.md      # 주차별 학습 기록 (막힌 지점 포함)
│   ├── 01_decisions.md         # 설계 결정 로그 (D-001, D-002, ...)
│   ├── 02_theory/              # 이론 문서 (W0~W8)
│   ├── 03_results/             # 결과 그림 + 해석
│   ├── 04_limitations.md       # 이 구현이 다루지 못하는 것
│   └── 05_glossary.md          # 약어 풀이
├── data/                       # 원본은 git 추적 안 함 (README에 다운로드 안내)
├── src/
│   ├── models/                 # ECM (1RC/2RC/히스테리시스)
│   ├── identification/         # HPPC 피팅, RLS
│   ├── estimators/             # KF/EKF/UKF/Dual EKF
│   ├── validation/             # NIS, 백색성, 스트레스 테스트
│   └── sop/                    # SOP 계산
├── notebooks/                  # 탐색적 분석
├── tests/                      # 단위 테스트
└── simulink/                   # W8: MIL 검증용
```

## 실행 환경

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## AI 도구 사용에 대해

구현 코드 작성과 문서 정리에 AI 도구를 활용했습니다. 대신 확보한 시간은
**모델 구조 선택, 파라미터 식별 실험 설계, 검증 방법론 수립**에
사용했습니다. 각 설계 결정의 근거와 폐기한 대안은
[docs/01_decisions.md](docs/01_decisions.md)에, 학습 과정에서 실제로
막혔던 지점과 해결 과정은 [docs/00_learning_log.md](docs/00_learning_log.md)에
기록했습니다.

## 라이선스

코드(`src/`, `tests/`, `notebooks/`)는 MIT, 문서(`docs/`)는 CC BY 4.0.
자세한 내용은 [LICENSE](LICENSE) 참고. 데이터는 각 원저작자의 라이선스를
따릅니다.
