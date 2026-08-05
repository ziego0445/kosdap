-- kosdap Supabase schema
-- 실행: Supabase 프로젝트의 SQL Editor에서 그대로 실행

create extension if not exists "uuid-ossp";

-- 종목별 원천 데이터 스냅샷 (수집 이력, 디버깅/재계산용)
create table if not exists raw_snapshots (
  id uuid primary key default uuid_generate_v4(),
  source text not null,               -- 'skhyb', 'smsn', 'yfinance:NVDA', ...
  value numeric,
  collected_at timestamptz not null default now()
);
create index if not exists idx_raw_snapshots_source_time
  on raw_snapshots (source, collected_at desc);

-- 종목별 최신/과거 추정치
create table if not exists predictions (
  id uuid primary key default uuid_generate_v4(),
  symbol text not null,               -- 'SAMSUNG' | 'SKHYNIX'
  current_price numeric not null,
  predicted_price numeric not null,
  change_percent numeric not null,
  confidence numeric not null,
  probability_up numeric not null,
  range_low numeric not null,
  range_high numeric not null,
  factors jsonb not null default '[]',
  is_weekend boolean not null default false,
  is_low_sample boolean not null default true,  -- 백테스트 표본이 작아 검증 중인 단계인지 (docs/PRD.md 4.2)
  sample_size_days integer not null default 0,
  created_at timestamptz not null default now()
);
create index if not exists idx_predictions_symbol_time
  on predictions (symbol, created_at desc);

-- 실제 종가/시간외가 (장마감 후 확정치)
create table if not exists actual_prices (
  id uuid primary key default uuid_generate_v4(),
  symbol text not null,
  price numeric not null,
  session text not null,              -- 'regular_close' | 'after_hours' | 'pre_market'
  trade_date date not null,
  created_at timestamptz not null default now()
);
create unique index if not exists idx_actual_prices_symbol_date_session
  on actual_prices (symbol, trade_date, session);

-- 예측 vs 실제 오차 집계 (일 단위)
create table if not exists prediction_accuracy (
  id uuid primary key default uuid_generate_v4(),
  symbol text not null,
  trade_date date not null,
  predicted_price numeric not null,
  actual_price numeric not null,
  error_percent numeric not null,
  created_at timestamptz not null default now()
);
create unique index if not exists idx_prediction_accuracy_symbol_date
  on prediction_accuracy (symbol, trade_date);

-- 토큰가 vs KRX 종가 베이시스 보정값 (docs/PRD.md 3.1)
create table if not exists basis_offsets (
  id uuid primary key default uuid_generate_v4(),
  symbol text not null,
  krx_close numeric not null,
  token_price numeric not null,
  offset_percent numeric not null,
  trade_date date not null,
  created_at timestamptz not null default now()
);
create unique index if not exists idx_basis_offsets_symbol_date
  on basis_offsets (symbol, trade_date);

-- 관리자 페이지용 실행 로그
create table if not exists admin_logs (
  id uuid primary key default uuid_generate_v4(),
  source text not null,
  status text not null,               -- 'ok' | 'error' | 'idle'
  detail text,
  created_at timestamptz not null default now()
);
create index if not exists idx_admin_logs_time on admin_logs (created_at desc);

-- RLS: 웹(anon key)은 읽기 전용, 쓰기는 predictor(service-role key)만 허용
alter table predictions enable row level security;
alter table prediction_accuracy enable row level security;
alter table admin_logs enable row level security;
alter table actual_prices enable row level security;
alter table raw_snapshots enable row level security;
alter table basis_offsets enable row level security;

create policy "public read predictions" on predictions
  for select using (true);
create policy "public read prediction_accuracy" on prediction_accuracy
  for select using (true);
create policy "public read admin_logs" on admin_logs
  for select using (true);

-- service-role key는 RLS를 우회하므로 predictor의 insert에는 별도 정책 불필요
