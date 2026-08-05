# kosdap

삼성전자(005930)·SK하이닉스(000660)의 다음 거래일 추정가격을, LLM이 아니라
실제 시장 데이터를 계산해서 보여주는 서비스.

자세한 내용은 [docs/PRD.md](docs/PRD.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 참고.

## 구조
```
apps/web/          Next.js 15 프론트 + 어드민
services/predictor/  Python 데이터 수집·계산 워커
supabase/schema.sql   DB 스키마
```

## 로컬 실행

### 1. Supabase
1. [supabase.com](https://supabase.com)에서 프로젝트 생성
2. SQL Editor에서 `supabase/schema.sql` 실행
3. 프로젝트 설정에서 URL / anon key / service-role key 확인

### 2. 웹 (`apps/web`)
```bash
cd apps/web
cp .env.local.example .env.local   # NEXT_PUBLIC_SUPABASE_URL / ANON_KEY 입력
npm install
npm run dev
```
http://localhost:3000 — Supabase 미설정 시에도 예시(mock) 데이터로 동작합니다.

### 3. 예측 워커 (`services/predictor`)
```bash
cd services/predictor
python -m venv .venv
source .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # SUPABASE_URL / SERVICE_ROLE_KEY 입력
python main.py                  # 1회 실행
python scheduler.py             # 반복 실행 (기본 5분 간격)
```
Supabase 환경변수 없이도 dry-run(콘솔 로그만 출력)으로 동작합니다.

## 현재 스캐폴딩 상태
- ✅ 화면: 메인/예측기록/관리자 페이지, mock 데이터로 렌더링 확인됨
- ✅ 예측 로직: 수동 가중합 스코어링 (`services/predictor/models/scoring.py`)
- ⚠️ 스텁(추후 구현 필요): KRX 시간외 데이터(`collectors/krx.py`), 공매도/수급
  데이터(`collectors/flows.py`), 베이시스 보정(`basis_offsets`)
- ⚠️ 미검증: Binance/Hyperliquid API 심볼·응답 필드는 실거래소 문서로 재확인 필요
