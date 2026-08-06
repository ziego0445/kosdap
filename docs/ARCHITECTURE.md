# kosdap 아키텍처

## 디렉토리 구조
```
kos/
├── apps/
│   └── web/                 # Next.js 15, 정적 export(output:"export") — GitHub Pages 배포 대상
│       ├── components/      # StockCard, FactorChart/HistoryChart(Chart.js), LiveDashboard 등
│       └── public/predictions.json  # predictor가 써주는 스냅샷 (gitignore됨, 런타임 산출물)
├── services/
│   └── predictor/           # Python: 수집 → 계산 → (Supabase 또는 JSON) 저장
│       ├── collectors/      # 데이터 소스별 수집 모듈 (tokenized/equities/macro/flows/krx/market_hours)
│       ├── models/          # fitted_weights.py(ridge 계수) + scoring.py
│       ├── notify.py        # 텔레그램 관리자 장애 알림
│       ├── scheduler.py     # 반복 실행 (기본 5분 간격)
│       └── main.py
├── supabase/
│   └── schema.sql           # 테이블 정의 (아직 실제 프로젝트 미생성)
├── .github/workflows/
│   └── deploy.yml           # GitHub Pages 배포 (현재 push/schedule 트리거 꺼둠 — 보류 중)
├── docs/
│   ├── PRD.md
│   └── ARCHITECTURE.md
└── README.md
```

## 데이터 흐름
```
[외부 소스]
  SAMSUNGUSDT/SKHYNIXUSDT(Bybit, 24/7), SKHYB/USDT(Binance, 교차검증)
  MU/NVDA/TSM/SOXX/SMH(Yahoo Finance), USD/KRW·DXY·VIX·10년물·BTC/ETH(Yahoo Finance)
  외국인/기관 순매수(네이버페이 증권, 일 1회)
  KRX 종가/장중 실시간가(Yahoo Finance)
        │
        ▼
services/predictor (Python, scheduler.py가 5분 간격 반복 실행)
  1. market_hours.get_session()으로 KRX 세션(open/pre_market/post_market/closed) 판정
     - open(정규장): 실시간 체결가를 그대로 사용, 예측 계산 자체를 생략
     - 그 외: models/scoring.py(ridge 회귀 계수)로 추정가 계산
  2. collectors/*.py가 원천 데이터 수집 → raw_snapshots(또는 dry-run 로그)
  3. 결과를 두 곳에 반영:
     a. db.py를 통해 Supabase predictions/actual_prices 테이블에 저장
        (SUPABASE_URL 미설정 시 dry-run으로 콘솔에만 로그)
     b. apps/web/public/predictions.json에 프론트가 바로 읽을 수 있는 형태로 저장
        (Supabase 연동 전 임시 브리지 — 로컬 개발/GitHub Actions 빌드 시 사용)
  4. 에러 발생 시 db.log_admin_event(status="error")가 자동으로 notify.py를
     통해 텔레그램 알림 전송
        │
        ▼
apps/web (Next.js, 정적 export)
  - app/page.tsx(서버 컴포넌트)가 빌드 시점의 predictions.json(또는 mock)을
    초기값으로 렌더링
  - components/live-dashboard.tsx(클라이언트)가 30초마다 predictions.json을
    직접 fetch해서 새로고침 없이 최신값 반영 (정적 사이트라 서버가 없어서
    router.refresh() 대신 이 방식을 씀)
```

## GitHub Pages 배포 파이프라인 (현재 보류)
`.github/workflows/deploy.yml`이 이미 구성돼 있음:
1. `python main.py` 실행 → `apps/web/public/predictions.json` 갱신
2. `npm run build` (정적 export, `apps/web/out/` 생성)
3. `actions/deploy-pages`로 GitHub Pages에 배포

원래는 push마다 + 10분 스케줄로 자동 실행하게 짰지만, 로컬 개발에 집중하기
위해 현재는 `workflow_dispatch`(수동 실행)만 열어둔 상태. 실제 배포 시
`deploy.yml`의 주석 처리된 `push`/`schedule` 블록을 다시 켤 것.

## 역할 분리 이유
- LightGBM/XGBoost, pandas 기반 통계 계산은 Python 생태계가 압도적으로 성숙
- Next.js/TS 쪽에 무거운 수치 계산 로직을 넣지 않음으로써 정적 사이트(GitHub Pages)와 데이터 워커의 배포/스케일링을 독립적으로 가져갈 수 있음
- 워커가 죽어도 웹은 마지막 저장된 predictions.json을 계속 보여줄 수 있음 (느슨한 결합)

## 주요 테이블 (supabase/schema.sql — 아직 실제 프로젝트 미생성)
- `raw_snapshots` — 소스별 원천 데이터 시계열 (수급 데이터 등)
- `predictions` — 종목별 추정가/구간/신뢰도/영향요인(JSON)
- `actual_prices` — 정규장 실시간가 및 시간외 체결가
- `prediction_accuracy` — 예측 vs 실제 오차, 일별 집계
- `basis_offsets` — 토큰가 vs KRX 종가 베이시스 보정값 (현재는 main.py에서 매 실행 시 즉석 계산, 별도 테이블 저장은 미구현)
- `admin_logs` — 수집/재계산 실행 로그

## 로컬 개발
1. `apps/web`: `npm install && npm run dev` → **http://localhost:3000/kosdap/** (basePath 주의)
2. `services/predictor`: `pip install -r requirements.txt && python main.py` (1회) 또는 `python scheduler.py` (반복)
3. (선택) Supabase 프로젝트 생성 후 `supabase/schema.sql` 실행, `.env`에 URL/키 설정 — 없어도 predictions.json 브리지로 로컬 확인 가능
