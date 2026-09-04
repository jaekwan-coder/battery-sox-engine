# src — 구현 코드

각 하위 폴더는 `docs/02_theory/`의 대응하는 주차 문서와 짝을 이룹니다.
코드를 보기 전에 해당 이론 문서를 먼저 읽는 것을 권장합니다.

| 폴더 | 대응 문서 | 역할 |
|---|---|---|
| `models/` | W1_electrochemistry_ecm | ECM 정의 (1RC/2RC/히스테리시스), 이산화 |
| `identification/` | W3_parameter_identification | HPPC 피팅, RLS 온라인 식별 |
| `estimators/` | W4_kalman_filter | KF/EKF/UKF/Dual EKF |
| `validation/` | W4_kalman_filter (M4.4-4.6) | NIS, 백색성, 스트레스 테스트 |
| `sop/` | W7_sop | SOP 계산 |

## 설계 원칙

- 각 모듈은 독립적으로 테스트 가능해야 함 (`tests/`에 대응 테스트 작성)
- 파라미터(R0, R1, C1 등)는 하드코딩하지 않고 `data/processed/`의
  룩업테이블에서 읽어오는 구조를 지향
- 새 모델 구조(예: SPMe)가 필요해지면 `src/electrochemical/` 같은
  새 폴더를 추가 — 기존 `models/`(ECM)는 그대로 유지해 비교 기준으로 남김
