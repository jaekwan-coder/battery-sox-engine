"""
Samsung INR21700-30T 시험 데이터 로더 (McMaster University / Kollmeyer)

이 파일이 하는 일: 사이클러가 저장한 원본 CSV(장비 메타정보 + Prog Time
문자열 등)를, src/identification/hppc.py가 바로 쓸 수 있는 형태
(초 단위 numpy 배열: time_s, voltage, current_A)로 변환한다.

파일 구조 확인 결과 (2026, data/raw/samsung_30t/25degC/729_HPPC.csv 실측):
    1~28행 : 장비/시험 메타정보 + 빈 줄 (스킵 대상)
    29행   : 진짜 컬럼 헤더 (Time Stamp, Step, Status, Prog Time, ...)
    30행   : 단위 표시 행 ([V], [A], [Ah] 등) - 데이터 아님, 스킵 대상
    31행~  : 실제 측정값

주의사항 (Readme 및 실측 확인):
- Time 컬럼이 따로 없고 "Prog Time"(전체 누적) / "Step Time"(스텝별
  리셋) 두 종류가 있다. 여러 펄스가 이어지는 HPPC에서는 전체 흐름을
  하나로 봐야 하므로 Prog Time을 사용한다.
- Prog Time은 "HH:MM:SS.mmm" 문자열이라 초 단위 숫자로 직접 변환해야
  find_pulse_edges 등 hppc.py의 함수들이 쓸 수 있다.
- Readme 경고대로 샘플링 간격이 구간마다 다를 수 있다 (휴지/충전 구간은
  저속 저장). ecm.py의 simulate()는 균일 dt를 가정하므로, 불균일한
  실측 데이터를 그대로 넣지 않도록 주의가 필요하다 — 이 로더는 우선
  "있는 그대로"의 불균일 시간축을 반환하고, 균일화(재샘플링)는
  후속 단계에서 필요시 별도로 처리한다(섣불리 보간하면 실제 펄스
  모양이 왜곡될 수 있어, 이 파일에서는 하지 않는다).
"""

from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class HPPCRawData:
    time_s: np.ndarray       # Prog Time을 초 단위로 변환한 것, t=0부터 시작
    voltage: np.ndarray      # [V]
    current_A: np.ndarray    # [A] (양수=방전, 음수=충전 — Status로 부호 확인 필요, 아래 참고)
    status: np.ndarray       # 'PAU'/'DCH'/'CHA' 등 원본 상태 문자열 (진단용)
    n_rows: int


def _find_header_row(filepath: str, marker: str = "Time Stamp") -> int:
    """
    메타정보 줄 수는 시험 종류마다 달라질 수 있으므로(예: Comment 줄 개수
    차이), 고정된 줄 번호(29)에 의존하지 않고 marker 문자열이 있는 줄을
    직접 찾는다. 이게 하드코딩보다 다른 시험 파일(C20DisCh 등)에도
    안전하게 재사용된다.
    """
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            if line.startswith(marker):
                return i
    raise ValueError(f"'{marker}'로 시작하는 헤더 행을 찾지 못했다: {filepath}")


def _prog_time_to_seconds(prog_time_series: pd.Series) -> np.ndarray:
    """
    'HH:MM:SS.mmm' 형태의 문자열을 t=0 기준 초 단위 숫자로 변환한다.
    HH가 24시간을 넘어갈 수 있으므로(장시간 시험) pandas의 to_timedelta를
    사용한다 — datetime이 아니라 timedelta로 다뤄야 자정을 넘는 문제가 없다.
    """
    td = pd.to_timedelta(prog_time_series)
    seconds = td.dt.total_seconds().to_numpy()
    return seconds - seconds[0]  # 이 파일의 시작을 t=0으로 재설정


def load_hppc_csv(filepath: str) -> HPPCRawData:
    """
    Samsung 30T 원본 HPPC CSV를 읽어 HPPCRawData로 변환한다.

    Current 부호 규약 확인 필요: 원본 데이터의 Status 컬럼으로 방전
    (DCH)/충전(CHA)을 구분할 수 있다. ecm.py/hppc.py는 "방전=양수"
    규약을 쓰므로, 원본 Current가 이미 이 규약을 따르는지 실측값으로
    확인 후 필요시 부호를 뒤집어야 한다 (아래 diagnose_sign_convention 참고).
    """
    header_row = _find_header_row(filepath)

    df = pd.read_csv(
        filepath,
        skiprows=header_row,   # 메타정보 스킵, 이 줄부터 읽기 시작
        header=0,              # 그 첫 줄을 컬럼명으로 사용
        skipfooter=0,
        engine="python",
    )
    # 헤더 다음 줄(단위 표시 행)을 제거. 이 행은 Voltage 컬럼 값이
    # "[V]"처럼 숫자가 아니므로, 숫자 변환이 안 되는 행으로 식별해 제거한다.
    df = df[pd.to_numeric(df["Voltage"], errors="coerce").notna()].reset_index(drop=True)

    time_s = _prog_time_to_seconds(df["Prog Time"])
    voltage = df["Voltage"].astype(float).to_numpy()
    current_A = df["Current"].astype(float).to_numpy()
    current_A = -current_A # 방전 = 음수(원본규약) -> 방전=양수 (ecm.py 규약)로 반전
    status = df["Status"].astype(str).to_numpy()

    return HPPCRawData(
        time_s=time_s, voltage=voltage, current_A=current_A,
        status=status, n_rows=len(df),
    )


def diagnose_sign_convention(data: HPPCRawData, n_examples: int = 3) -> None:
    """
    방전(DCH) 구간의 Current 부호가 양수인지 확인하는 진단 함수.
    hppc.py는 '방전=양수' 규약이므로, 만약 음수로 나온다면 호출하는
    쪽에서 current_A에 -1을 곱해줘야 한다. 코드로 자동 반전하지 않고
    사람이 확인하게 한 이유: 부호를 잘못 추정해 조용히 반전하면
    이후 모든 계산이 티 안 나게 틀어질 수 있기 때문이다.
    """
    dch_mask = data.status == "DCH"
    cha_mask = data.status == "CHA"
    print(f"DCH(방전) 구간 전류 예시: {data.current_A[dch_mask][:n_examples]}")
    print(f"CHA(충전) 구간 전류 예시: {data.current_A[cha_mask][:n_examples] if cha_mask.any() else '없음'}")
    print("-> DCH 예시가 양수면 규약과 일치, 음수면 current_A에 -1을 곱해서 사용할 것")


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/samsung_30t/25degC/729_HPPC.csv"
    data = load_hppc_csv(path)
    print(f"읽은 행 수: {data.n_rows}")
    print(f"시간 범위: 0 ~ {data.time_s[-1]:.1f}초 ({data.time_s[-1]/3600:.1f}시간)")
    print(f"전압 범위: {data.voltage.min():.3f} ~ {data.voltage.max():.3f} V")
    print(f"전류 범위: {data.current_A.min():.3f} ~ {data.current_A.max():.3f} A")
    print(f"고유 Status 값: {set(data.status)}")
    print()
    diagnose_sign_convention(data)
