"""과거 데이터로 ridge 회귀를 돌려 종목별 가중치(계수)를 재추정한다.

models/fitted_weights.py의 FITTED_MODELS를 만든 실제 스크립트 — 처음엔
세션 스크래치패드에만 있었는데(2026-08-06), 재현 불가능한 상태였어서 레포에
옮겨왔다. 데이터가 쌓여서 재적합할 때 이 스크립트를 그대로 다시 돌리면 됨.

표본이 작고(토큰 상장 이후 겹치는 기간뿐) 반도체 프록시끼리 상관관계가 높아서
(NVDA/MU/SOXX/TSM/SMH) 일반 OLS는 과적합 위험이 크다 -> numpy로 직접
closed-form ridge를 구현하고, alpha는 LOOCV로 고른다. sklearn 등 무거운
의존성은 추가하지 않는다.

실행:
    cd services/predictor
    pip install -r requirements.txt
    python scripts/fit_weights.py

출력된 coefficients/intercept/resid_std/n을 models/fitted_weights.py의
FITTED_MODELS에 수동으로 옮겨 적을 것 (자동 반영 아님 — 계수를 바꾸는 건
사람이 검토하고 반영해야 하는 일이라 의도적으로 수동 단계로 남겨둠).
"""

from __future__ import annotations

import datetime as dt
import json

import numpy as np
import pandas as pd
import requests
import yfinance as yf

# TODO(2026-08-17): SKHYNIX엔 나스닥 ADR(SKHY, collectors/adr.py) 피처가
# 추가됐는데("adr", models/fitted_weights.py에 수동 계수 0.6으로 임시
# 반영), 삼성전자는 대응 ADR 유동성이 없어 이 피처가 없다 — 이 스크립트는
# 아직 모든 종목이 같은 FEATURES를 공유한다고 가정하므로, 재적합 전에
# 종목별로 다른 FEATURES 집합을 다루도록 먼저 고쳐야 한다(SKHYNIX만
# "adr" 추가, SAMSUNG은 제외). 표본이 충분히 쌓이기 전까진 급하지 않음.
KRX = {"SAMSUNG": "005930.KS", "SKHYNIX": "000660.KS"}
BYBIT_SYMBOL = {"SAMSUNG": "SAMSUNGUSDT", "SKHYNIX": "SKHYNIXUSDT"}
FEATURES = ["token", "NVDA", "MU", "SOXX", "TSM", "SMH", "ES=F", "NQ=F", "KRW=X", "DX-Y.NYB", "^TNX", "^VIX", "BTC-USD", "ETH-USD"]
PROXIES = ["NVDA", "MU", "SOXX", "TSM", "SMH", "ES=F", "NQ=F"]
MACRO = ["KRW=X", "DX-Y.NYB", "^TNX", "^VIX", "BTC-USD", "ETH-USD"]
ALPHAS = [1, 3, 10, 30, 100, 300, 1000, 3000, 10000, 30000, 100000]

# 2026-07-31 KOSPI 사상 최대 등락일(숏스퀴즈+회장 장내매수)은 학습에서 제외 —
# 국내 수급 신호(flows.py) 없이는 이런 이벤트를 설명할 features가 없어서
# 계수를 왜곡시킴 (docs/PRD.md 4.2/4.3 참고). flows.py가 scoring에 실제로
# 반영되면 이 제외 처리를 재검토할 것.
OUTLIER_DATES = {dt.date(2026, 7, 31)}


def bybit_daily_klines(symbol: str, limit: int = 200) -> pd.Series:
    r = requests.get(
        "https://api.bybit.com/v5/market/kline",
        params={"category": "linear", "symbol": symbol, "interval": "D", "limit": limit},
        timeout=20,
    )
    r.raise_for_status()
    rows = r.json()["result"]["list"]
    data = {dt.datetime.fromtimestamp(int(row[0]) / 1000, tz=dt.UTC).date(): float(row[4]) for row in rows}
    s = pd.Series(data).sort_index()
    s.index = pd.to_datetime(s.index)
    return s


def close_series(ticker: str, period: str = "9mo") -> pd.Series:
    h = yf.Ticker(ticker).history(period=period, interval="1d")["Close"].dropna()
    h.index = h.index.tz_localize(None).normalize()
    return h


def ridge_fit(X: np.ndarray, y: np.ndarray, alpha: float) -> tuple[np.ndarray, float]:
    """closed-form ridge: beta = (X^T X + alpha*I)^-1 X^T y, 절편은 정규화 안 함."""
    Xc = X - X.mean(axis=0)
    yc = y - y.mean()
    beta = np.linalg.solve(Xc.T @ Xc + alpha * np.eye(X.shape[1]), Xc.T @ yc)
    intercept = y.mean() - X.mean(axis=0) @ beta
    return beta, intercept


def loocv_predictions(X: np.ndarray, y: np.ndarray, alpha: float) -> np.ndarray:
    n = len(y)
    preds = []
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        b, ic = ridge_fit(X[mask], y[mask], alpha)
        preds.append(X[i] @ b + ic)
    return np.array(preds)


def main() -> None:
    proxy_ret = {p: close_series(p).pct_change() * 100 for p in PROXIES}
    macro_ret = {m: close_series(m).pct_change() * 100 for m in MACRO}

    results = {}

    for symbol, krx_ticker in KRX.items():
        krx_close = close_series(krx_ticker)
        krx_ret = krx_close.pct_change() * 100
        token_ret = bybit_daily_klines(BYBIT_SYMBOL[symbol]).pct_change() * 100

        dates = krx_close.index.intersection(token_ret.index)[1:]
        rows, targets = [], []
        for d in dates:
            if d.date() in OUTLIER_DATES:
                continue
            if d not in krx_ret.index or pd.isna(krx_ret.loc[d]):
                continue
            vals = {"token": token_ret.get(d, np.nan)}
            vals.update({p: proxy_ret[p].get(d, np.nan) for p in PROXIES})
            vals.update({m: macro_ret[m].get(d, np.nan) for m in MACRO})
            if any(pd.isna(v) for v in vals.values()):
                continue
            rows.append([vals[f] for f in FEATURES])
            targets.append(float(krx_ret.loc[d]))

        X = np.array(rows)
        y = np.array(targets)
        n = len(y)

        cv_scores = {}
        for a in ALPHAS:
            preds = loocv_predictions(X, y, a)
            cv_scores[a] = float(np.mean((preds - y) ** 2))
        best_alpha = min(cv_scores, key=cv_scores.get)

        loocv_preds = loocv_predictions(X, y, best_alpha)
        loocv_mae = float(np.mean(np.abs(loocv_preds - y)))
        naive_mae = float(np.mean(np.abs(y)))  # "항상 0% 예측" out-of-sample 기준선

        beta, intercept = ridge_fit(X, y, best_alpha)
        resid = y - (X @ beta + intercept)
        resid_std = float(np.std(resid))

        print(f"\n=== {symbol} (n={n}) ===")
        print(f"  alpha grid MSE: {[(a, round(v, 3)) for a, v in cv_scores.items()]}")
        print(f"  선택된 alpha: {best_alpha}")
        print(f"  [out-of-sample] LOOCV MAE: {loocv_mae:.2f}%  vs naive(항상 0%) MAE: {naive_mae:.2f}%")
        print(f"  intercept: {intercept:.4f}")
        for f, b in zip(FEATURES, beta):
            print(f"  {f:>10s}: {b:+.4f}")
        print(f"  residual_std: {resid_std:.3f}%")

        results[symbol] = {
            "intercept": round(float(intercept), 4),
            "coefficients": {f: round(float(b), 4) for f, b in zip(FEATURES, beta)},
            "resid_std": round(resid_std, 3),
            "alpha": best_alpha,
            "n": n,
        }

    print("\n" + json.dumps(results, indent=2, ensure_ascii=False))
    print("\n위 결과를 models/fitted_weights.py의 FITTED_MODELS에 수동으로 반영할 것.")


if __name__ == "__main__":
    main()
