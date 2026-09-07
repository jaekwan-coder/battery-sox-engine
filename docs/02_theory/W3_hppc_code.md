# hppc.py 설계 — 코드 작성 전 계획

이 문서는 [`src/identification/hppc.py`](../../src/identification/hppc.py)를
**만들기 전에** 먼저 정리한 설계입니다. 왜 이런 함수들로 나눌 것인지,
왜 이 순서로 만들 것인지를 먼저 적어두고, 이 계획대로 코드를 만듭니다.

---

## 🟢 쉬운 버전 — 이 파일이 왜 필요한가

### 지금까지와 무엇이 다른가

`ecm.py`는 **"R0, R1, C1을 이미 안다고 치고, 전류를 넣으면 전압을
계산해주는" 도구**였습니다. `hppc.py`는 정반대 방향입니다.

> **"전압과 전류를 이미 안다고 치고(측정했으니까), 거꾸로 R0, R1,
> C1이 얼마였는지 알아내는 도구."**

$$\text{ecm.py: } R_0, R_1, C_1 \to \text{전압} \qquad\qquad \text{hppc.py: 전압} \to R_0, R_1, C_1$$

### 왜 실제 데이터 없이 먼저 만들 수 있는가

`ecm.py`가 "정답을 아는 상태에서 가짜 시험 문제를 만들어내는 기계"이기
때문입니다. 순서는 이렇습니다.

1. `ecm.py`에 **내가 이미 정한** 진짜 값(예: R0=0.02)을 넣는다
2. `ecm.py`로 "이런 전류를 흘렸더니 전압이 이렇게 나왔다"는 가짜
   실험 데이터를 만든다
3. 그 가짜 데이터를 `hppc.py`에 넣어서 R0를 다시 계산해본다
4. 1번에서 넣은 값(0.02)과 3번의 결과가 같은지 확인한다

**시험지를 만든 사람이 채점 기준(정답)을 이미 알고 있으니, 채점기가
맞는지 미리 검증할 수 있는 것**과 같습니다.

### 이 파일이 할 일 — 두 개의 계산

**계산 1. R0 찾기 — 뺄셈 하나로 끝남**

펄스가 시작되는 순간, 전압이 즉시 뚝 떨어집니다. 그 떨어진 양을 전류로
나누면 R0입니다.

$$R_0 = \frac{V_{\text{펄스 직전}} - V_{\text{펄스 직후}}}{I}$$

**계산 2. R1, C1 찾기 — 곡선의 모양을 보고 역산**

펄스가 끝난 뒤, 전압이 서서히 원래대로 돌아오는 구간(완화 구간)의
"모양"을 보고 R1, C1을 찾습니다. 물탱크(R1·C1)가 크면 천천히,
작으면 빠르게 돌아온다는 원리를 거꾸로 이용합니다.

### 함수를 몇 개로 나눌 것인가

| 함수 이름(예정) | 하는 일 |
|---|---|
| `find_pulse_edges` | 데이터에서 "펄스가 시작/끝나는 지점"을 찾아냄 |
| `extract_r0` | 계산 1 (즉시 강하 → R0) |
| `fit_relaxation` | 계산 2 (완화 곡선 → R1, C1), 여기서 곡선 피팅 사용 |
| `extract_hppc_parameters` | 위 셋을 순서대로 불러서, 하나의 펄스에서 R0/R1/C1을 한 번에 뽑아주는 대장 함수 |
| `validate_with_synthetic_data` | `ecm.py`로 가짜 데이터를 만들고, 위 함수들이 원래 값을 맞히는지 자동 확인 |

---

## 🔵 기술 버전 — 설계 세부

### 목표

`ecm.py`(순방향 모델)의 역과정, 즉 `W3_parameter_identification.md`
M3.3에서 설명한 절차를 코드화한다. `ecm.py`가 검증 도구를 겸하도록
설계했으므로(`W1_ecm_code.md` 설계 목표 1 참고), 실데이터 없이
합성검증(synthetic validation)까지 이 파일 하나로 완결한다.

### 함수 시그니처(안)

```python
def find_pulse_edges(current_A: np.ndarray, threshold: float = 1e-6) -> list[tuple[int, int]]:
    """전류가 0에서 벗어나는/돌아오는 인덱스 쌍(펄스 시작, 끝)을 찾는다."""

def extract_r0(voltage: np.ndarray, current_A: np.ndarray,
                pulse_start_idx: int, n_instant: int = 1) -> float:
    """펄스 시작 직전/직후 n_instant개 샘플의 평균 전압차 ÷ 전류로 R0 계산."""

def fit_relaxation(time_s: np.ndarray, voltage: np.ndarray,
                    initial_guess: dict) -> dict:
    """
    완화구간에 다중지수함수 V(t) = V_inf + A1*exp(-t/tau1) [+ A2*exp(-t/tau2)]
    를 scipy.optimize.curve_fit으로 피팅. R1=A1, C1=tau1/R1 로 환산.
    initial_guess는 M3.3에서 강조한 "초기값 민감성" 문제에 대응하기 위해
    필수 인자로 받는다(자동 추정 실패 시 사용자가 직접 지정 가능하게).
    """

def extract_hppc_parameters(time_s, voltage, current_A,
                             pulse_index: int = 0) -> ECMParameters:
    """위 함수들을 조합해 하나의 펄스에서 파라미터 세트를 완성."""

def validate_with_synthetic_data(true_params: ECMParameters,
                                  tolerance: float = 0.05) -> bool:
    """
    ecm.py로 합성 HPPC 데이터 생성 -> extract_hppc_parameters로 재추출
    -> true_params와 상대오차 tolerance 이내인지 확인.
    W3 M3.3 검증 원칙을 자동화한 것.
    """
```

### 설계 결정 (사전 계획, 코드 작성 시 `01_decisions.md`에 정식 등록 예정)

**`fit_relaxation`이 `initial_guess`를 필수로 받게 한 이유**: M3.3에서
비선형 피팅(Levenberg-Marquardt)이 초기값에 민감하다고 명시했다.
자동 추정 로직(예: 로그 스케일 선형근사로 초기 τ 추정)을 넣더라도,
실패 시 대체 경로로 수동 초기값을 항상 받을 수 있게 한다.

**`validate_with_synthetic_data`를 별도 함수로 분리한 이유**: 이 검증은
`hppc.py` 개발 중 반복적으로 실행될 것이므로, `tests/test_hppc.py`에서
그대로 재사용 가능하도록 라이브러리 함수로 만든다(테스트 코드에
검증 로직을 새로 짜지 않기 위함).

**2RC(R2, C2)를 이번 1차 구현에서 제외하는 이유**: M3.3에서 다중지수
피팅은 시상수가 가까우면 불안정하다고 확인했다(W2.2와 동일 원인).
1RC로 먼저 파이프라인 전체(추출→검증)를 완성해 안정성을 확보한 뒤,
2RC로 확장하며 시상수 분리 문제를 별도로 다룬다. 이는 D-001(2RC 채택)을
번복하는 것이 아니라, **구현 순서**의 문제다 — 최종 목표는 여전히 2RC.

### 검증 계획

1. R0 단독 검증: R0만 있는 합성 데이터(R1=C1=0)로 `extract_r0` 정확도 확인
2. 1RC 검증: `validate_with_synthetic_data`로 R0+R1+C1 전체 파이프라인 확인
3. 초기값 민감성 재현: 의도적으로 나쁜 `initial_guess`를 줘서 실패 양상 관찰
   (M3.3에서 언급한 문제를 코드로 직접 재현 — `docs/00_learning_log.md`에 기록 예정)
4. (2RC 확장 시) τ가 가까운 합성 데이터로 불안정성 재현 — W2.2 노트북과 대응

### 실데이터 적용은 이 문서의 범위 밖

위 1~4단계가 전부 통과한 뒤, `data/README.md`에 정리된 Samsung
INR21700 30T HPPC 데이터에 동일 함수를 적용한다. 이 단계는 별도
문서(`W3_hppc_results.md` 등, 실제 결과가 나온 뒤 작성)에서 다룬다.