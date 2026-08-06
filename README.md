# kosdap

삼성전자(005930)·SK하이닉스(000660)의 다음 거래일 추정가격을, LLM이 아니라
실제 시장 데이터를 계산해서 보여주는 서비스.

자세한 내용은 [docs/PRD.md](docs/PRD.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 참고.

## 구조
```
apps/web/          Next.js 15 프론트 (정적 export, GitHub Pages 배포 대상)
services/predictor/  Python 데이터 수집·계산 워커
supabase/schema.sql   DB 스키마 (아직 미연동 — 현재는 predictions.json 브리지로 대체)
.github/workflows/    GitHub Actions (배포는 보류 중, workflow_dispatch로만 수동 실행 가능)
```

## 로컬 실행

### 1. 웹 (`apps/web`)
```bash
cd apps/web
npm install
npm run dev
```
`next.config.ts`에 `basePath: "/kosdap"`이 설정돼 있어 로컬에서도
**http://localhost:3000/kosdap/** 로 접속해야 합니다 (루트 `/`는 안 뜸).
Supabase 미연동 상태에서는 predictor가 써주는 `public/predictions.json`
(있으면) 또는 mock 데이터로 동작합니다.

### 2. 예측 워커 (`services/predictor`)
```bash
cd services/predictor
python -m venv .venv
source .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # Supabase/텔레그램 키는 선택 — 없어도 dry-run으로 동작
python main.py                  # 1회 실행 (apps/web/public/predictions.json 갱신)
python scheduler.py             # 반복 실행 (기본 5분 간격, KRX 세션에 따라 실제가/추정가 자동 전환)
```

### 3. Supabase (아직 선택 사항)
1. [supabase.com](https://supabase.com)에서 프로젝트 생성
2. SQL Editor에서 `supabase/schema.sql` 실행
3. `apps/web/.env.local`, `services/predictor/.env`에 URL/키 입력

## 배포 (현재 보류 중)
GitHub Pages로 배포하는 워크플로우(`.github/workflows/deploy.yml`)는 이미
작성돼 있지만, 사용자 요청으로 `push`/`schedule` 트리거를 꺼두고
`workflow_dispatch`(수동 실행)만 열어뒀습니다. 실제 공개하려면:
1. 저장소를 public으로 전환 (GitHub Pages 무료 플랜은 public 저장소만 지원)
2. 저장소 Settings → Pages → Source를 "GitHub Actions"로 설정
3. `deploy.yml`의 주석 처리된 `push`/`schedule` 블록을 다시 활성화

## 현재 상태 (2026-08-06 기준)
- ✅ 화면: 메인/예측기록/관리자 페이지, Chart.js로 영향요인·예측vs실제 차트 표시
- ✅ 예측 로직: 종목별 ridge 회귀 계수 (`services/predictor/models/fitted_weights.py`) — 40일 표본 백테스트로 naive 기준선은 이기는 것 확인, 손으로 찍은 가중치 대비 우위는 아직 통계적으로 불확실 (docs/PRD.md 4.2)
- ✅ 실시간가/추정가 자동 전환: 정규장 운영 중엔 실제 체결가, 장외·주말엔 예측값 (`collectors/market_hours.py`)
- ✅ 데이터 소스 실측 검증 완료: Bybit(SAMSUNGUSDT/SKHYNIXUSDT), Yahoo Finance(해외 프록시·매크로), 네이버페이 증권(외국인/기관 순매수)
- ✅ 텔레그램 관리자 장애 알림 연동
- ⚠️ 스텁(추후 구현 필요): KRX 시간외 단일가(`collectors/krx.py`), 공매도비율(`collectors/flows.py`)
- ⚠️ Supabase 미연동 — 현재는 predictor가 `apps/web/public/predictions.json`을 직접 써주는 방식으로 로컬에서만 실데이터 확인 가능
