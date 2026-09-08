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
| W0 | 기초 정비 (회로·제어·확률) | [W0_foundations](docs/02_theory/W0_foundations.md) | ✅ | ✅ (검증 노트북) |
| W1 | 전기화학 → 등가회로(ECM) | [W1_electrochemistry_ecm](docs/02_theory/W1_electrochemistry_ecm.md) | ✅ | ✅ ([ecm.py](src/models/ecm.py)) |
| W2 | EIS와 나이퀴스트 선도 | [W2_eis](docs/02_theory/W2_eis.md) | ✅ | ✅ ([노트북](notebooks/00_rc_nyquist.ipynb)) |
| W3 | 파라미터 식별 (HPPC, RLS) | [W3_parameter_identification](docs/02_theory/W3_parameter_identification.md) | ✅ | ✅ (실측 Samsung 30T 데이터 적용) |
| W4-5 | 상태추정 (EKF) + 검증 | [W4_kalman_filter](docs/02_theory/W4_kalman_filter.md) | 🔲 (문서 미작성) | ✅ ([ekf.py](src/estimators/ekf.py)) |
| W6 | SOH (Dual EKF, ICA/DVA) | [W6_soh](docs/02_theory/W6_soh.md) | 🔲 | 🔲 |
| W7 | SOP (제약 하 최적화) | [W7_sop](docs/02_theory/W7_sop.md) | 🔲 | 🔲 |
| W8 | 제품화 (임베디드, 기능안전) | [W8_productionization](docs/02_theory/W8_productionization.md) | 🔲 | 🔲 |

### 지금까지의 핵심 성과 (2026)

Samsung INR21700-30T 실측 데이터(McMaster University 공개)로 등가회로
파라미터(R0, R1, C1, OCV)를 추출하고, 확장 칼만필터로 실시간 SOC
추정에 성공했습니다.

```
검증: 일부러 틀린 초기 SOC(50%, 진짜는 100%)에서 EKF 시작
  -> 10분 만에 오차 0.17%p로 수렴, 최종 오차 0.02%p
  -> 같은 조건 순수 쿨롱카운팅은 최종 17~50%p 오차 유지 (미보정)
```

과정에서 실측 데이터 특유의 버그 2건(펄스 인덱스 불일치, 이중 부호반전)을
직접 발견·수정했습니다. 상세 내용은 [학습 로그](docs/00_learning_log.md)
참고. **다만 이 검증은 모델이 만든 데이터로 모델을 다시 채점한
"쌍둥이 실험"이라는 한계가 있어, 실측 드라이브 사이클(UDDS 등)로
교차검증하는 것이 다음 과제입니다** ([한계](docs/04_limitations.md) 참고).

## 데이터

McMaster University(캐나다)에서 공개한 **LG 18650HG2** 및
**Samsung INR21700 30T** 데이터셋을 사용합니다. 각 데이터셋의 구조,
시험 블록별 목적, HPPC 포함 여부에 대한 주의사항은
**[data/README.md](data/README.md)** 를 참고하세요.

## 저장소 전체 구조

처음 오셨다면 이 트리만 보고도 "뭐가 어디 있는지" 파악할 수 있게
만들었습니다. `✅`는 지금 내용이 채워진 것, `🔲`는 폴더/틀만 만들어두고
아직 내용이 비어있는 것입니다.

```
battery-sox-engine/
│
├── README.md                    ✅ 지금 보고 있는 이 파일 (전체 안내)
├── LICENSE                      ✅ 코드(MIT) / 문서(CC BY 4.0) 라이선스
├── requirements.txt             ✅ 설치해야 할 파이썬 패키지 목록
│
├── docs/                        📖 "왜"를 설명하는 글 (코드 없음)
│   ├── START_HERE.md            ✅ 처음 오면 여기부터 — 읽는 순서 안내
│   ├── 00_learning_log.md       ✅ 주차별 학습 일지 (막힌 지점, 해결 과정)
│   ├── 01_decisions.md          ✅ 설계 결정 로그 (D-001, D-002, D-003)
│   ├── 04_limitations.md        ✅ 이 프로젝트가 다루지 못하는 것
│   ├── 05_glossary.md           ✅ 약어 전체 풀이 (SOC, ECM, HPPC 등)
│   │
│   ├── 02_theory/               📖 주차별 이론 문서
│   │   ├── W0_foundations.md              ✅ 회로·제어·확률 기초 8문항
│   │   ├── W1_electrochemistry_ecm.md     ✅ 전기화학 → 등가회로(ECM)
│   │   ├── W2_eis.md                      ✅ EIS와 나이퀴스트 선도
│   │   ├── W3_parameter_identification.md ✅ 파라미터 식별(HPPC, RLS)
│   │   ├── W4_kalman_filter.md            🔲 칼만필터 (목차만 있음)
│   │   ├── W6_soh.md                      🔲 SOH (목차만 있음)
│   │   ├── W7_sop.md                      🔲 SOP (목차만 있음)
│   │   └── W8_productionization.md        🔲 제품화 (목차만 있음)
│   │
│   └── 03_results/              📊 결과 그림
│       ├── README.md            ✅ 그림 채워나가는 방식 설명
│       └── ocv_curve_25degc.png ✅ OCV(SOC) + 히스테리시스 그래프
│
├── data/                        🗄️ 실험 데이터 (원본 파일은 안 올림)
│   ├── README.md                ✅ 데이터셋 구조·출처·다운로드 방법
│   ├── raw/                     ✅ Samsung 30T 실측 원본 (git 추적 제외)
│   └── processed/               ✅ 추출 결과 표
│       ├── 25degC_hppc_params.csv   ✅ SOC별 R0/R1/C1 (139개 펄스)
│       └── 25degC_ocv_curve.csv     ✅ OCV(SOC) 곡선
│
├── src/                         🔧 실제로 동작하는 코드
│   ├── README.md                ✅ 이 폴더 전체의 설계 원칙 설명
│   ├── __init__.py              ✅ (빈 파일, "여긴 파이썬 패키지"라는 표시만)
│   │
│   ├── models/                  ✅ 배터리를 회로로 표현하는 코드
│   │   ├── README.md            ✅ 무엇을 담을 폴더인지 설명
│   │   ├── ecm.py               ✅ 2RC+히스테리시스 ECM (고정 파라미터)
│   │   └── dynamic_ecm.py       ✅ SOC별 실시간 파라미터 갱신 시뮬레이터
│   │
│   ├── identification/          ✅ 실측 데이터에서 파라미터 뽑는 코드
│   │   ├── README.md            ✅ 계획 설명
│   │   ├── samsung_loader.py    ✅ Samsung 30T CSV 로더 (부호반전 포함)
│   │   ├── hppc.py              ✅ HPPC 펄스 -> R0/R1/C1 추출
│   │   ├── extract_soc_table.py ✅ SOC별 파라미터 표 자동 생성
│   │   ├── extract_ocv_curve.py ✅ C20 데이터 -> OCV(SOC) 곡선
│   │   ├── plot_ocv_curve.py    ✅ OCV 곡선 시각화
│   │   └── parameter_lookup.py  ✅ 표 -> "SOC 넣으면 값 반환" 함수 포장
│   │
│   ├── estimators/              ✅ 실시간 SOC 추정 코드
│   │   ├── README.md            ✅ 계획 설명
│   │   ├── __init__.py          ✅ (빈 파일)
│   │   └── ekf.py               ✅ 확장 칼만필터 — 실시간 SOC 추정 성공
│   │
│   ├── validation/               🔲 NIS 등 정식 통계 검증 (다음 과제)
│   │   ├── README.md            ✅ 계획 설명만 있음
│   │   └── __init__.py          ✅ (빈 파일)
│   │
│   └── sop/                     🔲 출력 한계 계산 코드 (W7에서 작업)
│       ├── README.md            ✅ 계획 설명만 있음
│       └── __init__.py          ✅ (빈 파일)
│
├── tests/                       🧪 src/ 코드가 맞는지 검사하는 코드
│   ├── README.md                ✅ 테스트 작성 규칙 설명
│   └── test_ecm.py              ✅ ecm.py 검증 (6개 테스트, 전부 통과)
│
├── notebooks/                   🔬 그래프 그려보는 실험 공간
│   ├── README.md                ✅ 노트북 작성 규칙 설명
│   └── 00_rc_nyquist.ipynb      ✅ 나이퀴스트 반원 시뮬레이션 (실행결과 포함)
│
└── simulink/                    🔲 W8에서 쓸 MIL 검증용 (아직 비어있음)
    └── README.md                ✅ 계획 설명만 있음
```

### 지금 당장 봐야 할 파일 셋만 고르면

처음이라 뭐부터 볼지 모르겠다면, 아래 세 개만 먼저 보시면 됩니다.

1. **`docs/START_HERE.md`** — 전체를 어떤 순서로 읽어야 하는지
2. **`docs/00_learning_log.md`** — 실제로 겪은 버그와 해결 과정 (가장 서사적인 문서)
3. **`src/estimators/ekf.py`** — 최종 결과물: 실측 데이터 기반 실시간 SOC 추정기

### `🔲`가 왜 아직 남아있는가

W0~W5(칼만필터까지)는 이론과 구현이 완료됐습니다. W6(SOH)~W8(제품화)은
아직 손대지 않았는데, **"핵심 경로"(W0~W5)와 "여유 있으면 하는 것"
(W6~W8)을 의도적으로 나눠서 진행**했기 때문입니다. 이 프로젝트가
증명하려던 핵심 — 실측 데이터에서 파라미터를 뽑아 칼만필터로 SOC를
추정하는 것 — 은 이미 W5에서 완결됐습니다.

## 실행 환경

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 코드를 처음 보실 때

이 저장소의 코드(`src/`, `tests/`)를 처음 여신다면, 한 줄씩 다 읽으려
하지 않아도 됩니다. 아래 순서로 "구조"만 먼저 파악하는 걸 권합니다.

1. 파일 안에 `class`가 몇 개 있는지 (몇 개의 "물건"이 정의되어 있나)
2. 각 `class` 안에 `def`가 몇 개 있는지 (그 물건이 할 수 있는 일이 몇 개인가)
3. 가장 중요해 보이는 함수 하나를 골라 입력·출력만 먼저 확인
4. 계산 본문(수식이 있는 줄)은 필요할 때만 연다

`ecm.py`의 경우, `output_voltage` 함수의 마지막 줄이
`docs/02_theory/W1_electrochemistry_ecm.md`의 단자전압 공식과 그대로
대응됩니다 — 코드가 특별한 게 아니라 이론을 그대로 옮겨놓은 것입니다.

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