import pandas as pd

def basic_portfolio_metrics(df: pd.DataFrame, cash: float = 0.0, base_currency: str = "USD"):
    if df.empty:
        return {"total_value": cash, "positions": 0, "base_currency": base_currency}

    df = df.copy()
    df["position_value"] = df["quantity"] * df["price"]
    total_positions = df["position_value"].sum()
    total_value = total_positions + cash
    weights = df["position_value"] / total_value if total_value else 0
    sector_mix = (
        df.groupby(df.get("sector", pd.Series(["UNKNOWN"] * len(df))))["position_value"]
        .sum()
        .sort_values(ascending=False)
        .to_dict()
    )
    top_holdings = (
        df.sort_values("position_value", ascending=False)[["symbol", "position_value"]]
        .head(10).to_dict(orient="records")
    )

    return {
        "base_currency": base_currency,
        "cash": float(cash),
        "total_value": float(total_value),
        "num_positions": int(len(df)),
        "sector_mix": sector_mix,
        "top_holdings": top_holdings,
        "concentration_hhi": float((weights**2).sum() if hasattr(weights, "sum") else 0.0),
    }
