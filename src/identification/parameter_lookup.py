"""
파라미터 룩업테이블 — CSV 표를 "SOC를 넣으면 값을 돌려주는 함수"로 포장

이론적 배경: docs/02_theory/W3_parameter_identification.md
("SOC 10%씩 내려가며 R0(SOC), R1(SOC), C1(SOC) 룩업테이블")

지금까지 만든 건 "표(CSV)"였다. 하지만 ecm.py나 앞으로 만들 칼만필터는
"지금 SOC가 이거니까 R0가 얼마냐"를 실시간으로 물어봐야 한다. 이 파일은
그 다리 역할을 한다: 표 → 보간 함수.

대표값 선택 기준 (설계 결정, 01_decisions.md에 정식 등록 예정):
같은 SOC 지점에 1C/2C/6C/12C 등 여러 C-rate 펄스가 섞여 있다
(HPPC 프로토콜 자체가 그렇게 설계됨, W3_parameter_identification.md
M3.1 참고). ecm.py의 ECM 클래스는 현재 "고정된 스칼라 R0/R1/C1"을
가정하므로(SOC별로 하나의 값만 필요), 여러 후보 중 하나를 대표값으로
골라야 한다. 1C(약 3A, 셀의 공칭전류) 방전 펄스를 대표값으로 선택했다
- 가장 표준적인 사용 조건이고, 큰 전류일수록 완화구간 관찰시간
부족으로 R1/C1 신뢰도가 떨어진다는 게 이미 확인되었기 때문이다
(docs/00_learning_log.md의 hppc.py 실데이터 적용 항목 참고).

온도에 대한 한계: 현재는 25도 데이터만 있어 온도축은 고정되어 있다.
다른 온도 데이터가 추가되면 이 모듈을 SOC x 온도 2차원으로 확장해야
한다 - 지금은 알려진 한계로 남겨둔다.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d


class ECMParameterLookup:
    """
    SOC를 넣으면 R0, R1, C1, OCV, dOCV/dSOC를 돌려주는 통합 조회 객체.

    ecm.py의 ECM 클래스는 현재 이 값들을 "생성 시점에 고정된 스칼라"로
    받는 구조라서, 이 클래스의 출력을 그대로 ECMParameters에 넣으면
    "그 SOC 하나에서만 정확한" 스냅샷 모델이 된다. SOC가 계속 변하는
    실제 시뮬레이션(주행)에서는, 매 스텝마다 이 클래스로 새 파라미터를
    조회해 ECM을 다시 만들거나(비용 큼), ECM 자체를 SOC-의존적으로
    확장해야 한다 - 이건 다음 단계 과제로 명시해둔다.
    """

    def __init__(self, hppc_csv_path: str, ocv_csv_path: str,
                 target_current_A: float = 3.0, current_tolerance_A: float = 0.5):
        """
        Parameters
        ----------
        hppc_csv_path : extract_soc_table.py가 만든 R0/R1/C1 표
        ocv_csv_path : extract_ocv_curve.py가 만든 OCV(SOC) 표
        target_current_A : 대표값으로 쓸 펄스 전류 (기본 1C=3A)
        current_tolerance_A : target 주변 이 범위 안의 펄스만 대표값 후보로 인정
        """
        self.hppc_df = pd.read_csv(hppc_csv_path)
        self.ocv_df = pd.read_csv(ocv_csv_path)
        self._build_rc_interpolators(target_current_A, current_tolerance_A)
        self._build_ocv_interpolators()

    def _build_rc_interpolators(self, target_current_A, tolerance):
        df = self.hppc_df
        mask = (df["pulse_current_A"] - target_current_A).abs() <= tolerance
        selected = df[mask].sort_values("soc_at_pulse_start")

        if len(selected) < 2:
            raise ValueError(
                f"target_current_A={target_current_A}A 근방(±{tolerance}A) "
                f"펄스가 {len(selected)}개뿐이라 보간에 부족하다. "
                f"tolerance를 늘리거나 target_current_A를 조정할 것."
            )

        self.rc_soc_points = selected["soc_at_pulse_start"].to_numpy()
        self._r0_interp = interp1d(
            self.rc_soc_points, selected["R0"].to_numpy(),
            bounds_error=False, fill_value=(selected["R0"].iloc[0], selected["R0"].iloc[-1]),
        )
        self._r1_interp = interp1d(
            self.rc_soc_points, selected["R1"].to_numpy(),
            bounds_error=False, fill_value=(selected["R1"].iloc[0], selected["R1"].iloc[-1]),
        )
        self._c1_interp = interp1d(
            self.rc_soc_points, selected["C1"].to_numpy(),
            bounds_error=False, fill_value=(selected["C1"].iloc[0], selected["C1"].iloc[-1]),
        )
        self.n_rc_points = len(selected)

    def _build_ocv_interpolators(self):
        soc_grid = self.ocv_df["soc"].to_numpy()
        ocv_vals = self.ocv_df["ocv_mean"].to_numpy()
        self._ocv_interp = interp1d(
            soc_grid, ocv_vals, bounds_error=False,
            fill_value=(ocv_vals[0], ocv_vals[-1]),
        )
        # 해석적 미분 대신 스플라인 기반 미분 사용 - W0 Q4에서 다룬 대로
        # 룩업테이블을 그냥 차분하면 노이즈가 커지므로, 부드럽게 만든 뒤 미분
        from scipy.interpolate import UnivariateSpline
        spline = UnivariateSpline(soc_grid, ocv_vals, k=3, s=len(soc_grid) * 1e-6)
        self._ocv_slope_interp = spline.derivative()

    def R0(self, soc: float) -> float:
        return float(self._r0_interp(soc))

    def R1(self, soc: float) -> float:
        return float(self._r1_interp(soc))

    def C1(self, soc: float) -> float:
        return float(self._c1_interp(soc))

    def OCV(self, soc) -> np.ndarray:
        """ecm.py의 ocv_fn 시그니처(배열 입력/출력)와 호환되게 만듦."""
        soc_arr = np.atleast_1d(soc)
        return self._ocv_interp(soc_arr)

    def OCV_slope(self, soc) -> np.ndarray:
        soc_arr = np.atleast_1d(soc)
        return self._ocv_slope_interp(soc_arr)

    def snapshot_at(self, soc: float, Q_Ah: float = 3.0):
        """
        특정 SOC 하나에서의 스냅샷 파라미터를 ecm.py의 ECMParameters로
        만들어준다. 그 SOC 근방에서만 유효한 정적 모델이 필요할 때 사용.
        (SOC가 크게 변하는 시뮬레이션에는 부적합 - 클래스 docstring 참고)
        """
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "models"))
        from ecm import ECMParameters
        return ECMParameters(
            R0=self.R0(soc), R1=self.R1(soc), C1=self.C1(soc),
            R2=1e-9, C2=1e-9,  # 현재 1RC까지만 있음 (2RC 확장은 다음 과제)
            Q_Ah=Q_Ah,
        )

    def summary(self) -> str:
        lines = [
            f"R0/R1/C1 대표 펄스 개수: {self.n_rc_points}개",
            f"SOC 커버 범위(R0/R1/C1): {self.rc_soc_points.min()*100:.1f}% ~ {self.rc_soc_points.max()*100:.1f}%",
            f"OCV 격자점 개수: {len(self.ocv_df)}",
        ]
        return "\n".join(lines)


if __name__ == "__main__":
    hppc_path = sys.argv[1] if len(sys.argv) > 1 else "data/processed/25degC_hppc_params.csv"
    ocv_path = sys.argv[2] if len(sys.argv) > 2 else "data/processed/25degC_ocv_curve.csv"

    lookup = ECMParameterLookup(hppc_path, ocv_path)
    print(lookup.summary())
    print()
    print("SOC(%)    R0        R1         C1        OCV")
    for soc_pct in [100, 90, 80, 70, 60, 50, 40, 30, 20, 10, 5]:
        soc = soc_pct / 100
        print(f"{soc_pct:5d}   {lookup.R0(soc):.5f}   {lookup.R1(soc):.5f}   "
              f"{lookup.C1(soc):9.2f}   {lookup.OCV(soc)[0]:.4f}")