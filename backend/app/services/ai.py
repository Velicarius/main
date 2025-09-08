import os
from typing import Dict, List

def _rule_based_takeaways(metrics: Dict, positions_df) -> List[str]:
    notes = []
    # Concentration
    hhi = metrics.get("concentration_hhi", 0)
    if hhi > 0.2:
        notes.append("High concentration detected; consider diversifying top holdings.")
    # Cash
    cash = metrics.get("cash", 0.0)
    tv = metrics.get("total_value", 0.0)
    if tv and cash / tv > 0.25:
        notes.append("Large cash buffer; you could stage entries or deploy via DCA.")
    # Sector
    sector_mix = metrics.get("sector_mix", {})
    if sector_mix:
        biggest = next(iter(sector_mix))
        notes.append(f"Sector tilt toward {biggest}; review cyclicality and macro exposure.")
    return notes or ["No immediate red flags in basic metrics."]

def generate_insights(metrics: Dict, positions_df):
    # Use OpenAI if API key present; otherwise simple rules.
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return _rule_based_takeaways(metrics, positions_df)

    # Minimal lightweight prompt; keep it safe and cheap
    try:
        import httpx, json
        base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        prompt = (
            "You are a risk-aware portfolio coach. Given JSON metrics and positions, "
            "produce 3–5 concise, actionable insights (no disclaimers)."
        )
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Metrics: {metrics}\nPositions sample: {positions_df.head(10).to_dict()}"}
            ],
            "temperature": 0.2,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=20.0) as client:
            r = client.post(f"{base}/chat/completions", json=payload, headers=headers)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            return [s.strip("- • ") for s in content.splitlines() if s.strip()]
    except Exception:
        # Fallback if API fails
        return _rule_based_takeaways(metrics, positions_df)
