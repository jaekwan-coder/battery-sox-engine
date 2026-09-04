# 데이터

## 1차 데이터셋: LG 18650HG2

- 출처: Kollmeyer, P., McMaster University, Mendeley Data
- URL: https://data.mendeley.com/datasets/cp3473x7xv/3
- 구성: HPPC 시험, 여러 온도(-20~40℃), 드라이브 사이클
  (UDDS, US06, HWFET, LA92)
- 다운로드 후 `data/raw/`에 압축 해제 (git 추적 대상 아님)

## 다운로드 방법

```bash
# 수동 다운로드 후 압축 해제 권장 (Mendeley는 프로그래밍 방식
# 다운로드에 제약이 있을 수 있음)
mkdir -p data/raw/lg_hg2
# 위 URL에서 다운로드한 파일을 data/raw/lg_hg2/ 에 배치
```

## 보조 데이터셋 (필요 시)

- CALCE (University of Maryland) — 노화 데이터
- Oxford Battery Degradation Dataset — ICA/DVA 실습용
- NASA PCoE — RUL 관련 참고

## 데이터를 git에 올리지 않는 이유

용량이 크고(수백 MB~GB), 원본이 공개되어 있어 재다운로드가 가능하므로
저장소에 포함하지 않습니다. 대신 `data/processed/`에 생성한 요약
통계나 파라미터 룩업테이블(용량이 작은 것)은 예외적으로 커밋 대상에
포함할 수 있습니다 — 이 경우 `.gitignore`에서 해당 파일을 명시적으로
제외 처리(`!data/processed/params_lookup.csv` 형태)하세요.
