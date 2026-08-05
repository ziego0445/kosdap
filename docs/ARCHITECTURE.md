# kosdap 아키텍처

## 디렉토리 구조
```
kos/
├── apps/
│   └── web/                 # Next.js 15 (프론트 + 어드민 API 라우트)
├── services/
│   └── predictor/           # Python: 수집 → 계산 → Supabase 저장
│       ├── collectors/      # 데이터 소스별 수집 모듈
│       ├── models/          # 가중합 스코어링 + (추후) LightGBM/XGBoost
│       ├── scheduler.py     # 소스별 다른 주기로 수집 실행
│       └── main.py
├── supabase/
│   └── schema.sql           # 테이블 정의
├── docs/
│   ├── PRD.md
│   └── ARCHITECTURE.md
└── README.md
```

## 데이터 흐름
```
[외부 소스]
  SKHYB/USDT(Binance), SMSN/USD(Hyperliquid),
  MU/NVDA/SOXX/TSM(Yahoo Finance), USD/KRW, DXY, VIX,
  KOSPI200 야간선물, 공매도/수급(일1회), KRX 시간외
        │
        ▼
services/predictor (Python, 소스별 다른 주기로 스케줄)
  1. collectors/*.py 가 원천 데이터 수집 → raw_snapshots 테이블
  2. models/scoring.py 가 가중합 계산 (초기) / ML 모델 추론 (고도화 후)
  3. predictions 테이블에 추정가/신뢰구간/영향요인 저장
  4. 장마감 시 실제 종가가 확정되면 prediction_accuracy 테이블에 오차 기록
        │
        ▼
Supabase (Postgres)
        │
        ▼
apps/web (Next.js)
  - 서버 컴포넌트/Route Handler에서 Supabase 조회 → 화면 렌더
  - /admin 페이지의 "새로고침/재계산" 버튼은 API route를 통해
    predictor 서비스에 트리거 요청(HTTP) 또는 Supabase에 job row insert
```

## 역할 분리 이유
- LightGBM/XGBoost, pandas 기반 통계 계산은 Python 생태계가 압도적으로 성숙
- Next.js/TS 쪽에 무거운 수치 계산 로직을 넣지 않음으로써 웹 배포(Vercel 등)와 데이터 워커의 배포/스케일링을 독립적으로 가져갈 수 있음
- 워커가 죽어도 웹은 마지막 저장된 예측치를 계속 보여줄 수 있음 (느슨한 결합)

## 주요 테이블 (supabase/schema.sql)
- `raw_snapshots` — 소스별 원천 데이터 시계열
- `predictions` — 종목별 추정가/구간/신뢰도/영향요인(JSON)
- `actual_prices` — 실제 종가/시간외가
- `prediction_accuracy` — 예측 vs 실제 오차, 일별 집계
- `basis_offsets` — 토큰가 vs KRX 종가 베이시스 보정값
- `admin_logs` — 수집/재계산 실행 로그

## 로컬 개발
1. `apps/web`: `npm install && npm run dev`
2. `services/predictor`: `pip install -r requirements.txt && python main.py`
3. Supabase 프로젝트 생성 후 `supabase/schema.sql` 실행, `.env`에 URL/키 설정
