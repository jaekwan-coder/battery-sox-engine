# Battery SOX Engine

리튬이온 배터리의 SOC(State of Charge) · SOH(State of Health) · SOP(State of Power)를
등가회로모델(ECM)과 칼만필터 계열 상태추정기로 구현하는 프로젝트입니다.

## 이 저장소의 목적

세 가지를 동시에 겨냥합니다.

1. **개인 학습 기록**: 전기·전자공학 학부 졸업 후 세부 이론을 다시 다지며,
   BMS(Battery Management System) 알고리즘 엔지니어 직무를 8주 커리큘럼으로
   따라잡는 과정. 실패한 시도와 판단 근거를 숨기지 않고 남깁니다.
2. **참고 자료**: 같은 방향을 준비하는 다른 학습자가 이론적 배경부터
   구현까지 이어지는 흐름을 그대로 따라갈 수 있도록 정리합니다.
3. **포트폴리오**: 채용 지원 시 제출 가능한 수준의 완성도를 목표로 합니다.

## 왜 이 문제가 어려운가 (한 줄 요약)

배터리는 잔량 센서가 없습니다. 측정 가능한 건 단자전압·전류·온도뿐이고,
알고 싶은 건 측정 불가능한 내부 상태(SOC/SOH/SOP)입니다. 이 간극을
물리 모델과 확률적 추정으로 메우는 것이 이 프로젝트의 전부입니다.
자세한 배경은 [`docs/02_theory/W0_foundations.md`](docs/02_theory/W0_foundations.md) 참고.

## 로드맵

| 주차 | 내용 | 문서 | 상태 |
|---|---|---|---|
| W0 | 기초 정비 (회로·제어·확률 최소 세트) | [W0_foundations](docs/02_theory/W0_foundations.md) | ✅ |
| W1-2 | 셀→회로 번역 (ECM, EIS) | [W1_electrochemistry_ecm](docs/02_theory/W1_electrochemistry_ecm.md), [W2_eis](docs/02_theory/W2_eis.md) | ✅ (이론) / 🔲 (구현) |
| W3 | 파라미터 식별 (HPPC, RLS) | [W3_parameter_identification](docs/02_theory/W3_parameter_identification.md) | 🔲 |
| W4-5 | 상태추정 엔진 (EKF/UKF) + 검증 | [W4_kalman_filter](docs/02_theory/W4_kalman_filter.md) | 🔲 |
| W6 | SOH (Dual EKF, ICA/DVA) | [W6_soh](docs/02_theory/W6_soh.md) | 🔲 |
| W7 | SOP (제약 하 최적화) | [W7_sop](docs/02_theory/W7_sop.md) | 🔲 |
| W8 | 제품화 (임베디드, 기능안전) | [W8_productionization](docs/02_theory/W8_productionization.md) | 🔲 |

전체 학습 흐름은 [`docs/00_learning_log.md`](docs/00_learning_log.md)에서,
설계 결정 근거는 [`docs/01_decisions.md`](docs/01_decisions.md)에서 추적할 수 있습니다.

## 데이터

[LG 18650HG2 데이터셋](https://data.mendeley.com/datasets/cp3473x7xv/3)
(Kollmeyer, McMaster University, Mendeley Data 공개)을 1차 데이터로 사용합니다.
다운로드 및 구조는 [`data/README.md`](data/README.md) 참고.

## 저장소 구조

```
battery-sox-engine/
├── docs/
│   ├── 00_learning_log.md      # 주차별 학습 기록 (개인 로그, 실패 포함)
│   ├── 01_decisions.md         # 설계 결정 로그 (D-001, D-002, ...)
│   ├── 02_theory/              # 개념 설명 (재사용 가능한 참고자료)
│   ├── 03_results/             # 결과 그림 + 해석
│   └── 04_limitations.md       # 이 구현이 다루지 못하는 것
├── data/
│   ├── raw/                    # 원본 (git 추적 안 함)
│   └── processed/              # 전처리 결과 (git 추적 안 함)
├── src/
│   ├── models/                 # ECM (1RC/2RC/히스테리시스)
│   ├── identification/         # HPPC 피팅, RLS
│   ├── estimators/             # KF/EKF/UKF/Dual EKF
│   ├── validation/             # NIS, 백색성, 스트레스 테스트
│   └── sop/                    # SOP 계산
├── notebooks/                  # 탐색적 분석 (정리된 로직은 src로 이동)
├── tests/                      # 단위 테스트
└── simulink/                   # W8: MIL 검증용 모델
```

## 실행 환경

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 이 저장소를 참고자료로 쓰려는 분께

`docs/02_theory/`는 독립적으로 읽을 수 있게 썼습니다. W0부터 순서대로 읽으면
"왜 이 개념이 필요한가"가 앞 문서에서 다음 문서로 이어지도록 구성했습니다.
각 문서 끝에는 그 개념이 이후 어느 모듈에서 다시 쓰이는지 표시해 두었습니다.

오류나 개선점을 발견하시면 이슈로 남겨주세요.

## 라이선스

코드는 MIT 라이선스, 문서(`docs/`)는 CC BY 4.0을 따릅니다.
자세한 내용은 [`LICENSE`](LICENSE) 참고.
