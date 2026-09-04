# notebooks — 탐색적 분석

Jupyter 노트북은 **탐색과 시각화 용도로만** 사용합니다. 재사용되는 로직
(피팅 함수, 필터 클래스 등)은 정리되는 대로 `src/`로 옮기고, 노트북에서는
`src`를 import해서 사용하세요. 노트북에 로직이 그대로 쌓이면 나중에
테스트하기 어렵습니다.

## 명명 규칙

`{순번}_{내용}.ipynb`. 예: `00_rc_nyquist.ipynb`, `01_discretization.ipynb`

## 계획된 노트북 (W0)

- `00_rc_nyquist.ipynb`: RC 병렬 임피던스를 ω 0→∞로 계산해 나이퀴스트
  평면에 플롯 (`docs/02_theory/W0_foundations.md` Q2 검증)
- `01_discretization.ipynb`: 전진오일러 vs ZOH 비교, Δt/τ 비율별
  안정성 관찰 (Q8 검증)
