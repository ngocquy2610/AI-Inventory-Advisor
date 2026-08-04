# Module 2 — Forecast

This is the most distinctly 'AI' part of the system. Instead of a simple stock ÷ daily-sales division, the forecast engine adjusts for trend, seasonality, promotions, incoming shipments, and **real-world news context** to estimate a realistic stock-out date.

## Features

- Baseline days-of-cover calculation (current stock / consumption rate)
- Trend-adjusted forecasting (rising/falling demand curves)
- Seasonality and promotion-uplift modeling
- Incoming shipment awareness (purchase orders already in transit)
- Confidence range on the projected stock-out date, not just a single number
- **Real-world news signal**: queries Tavily for local & world news relevant to the store's geo-location and current local time, then adjusts the confidence band and consumption uplift accordingly

## Flow

1. Pull the Consumption Profile for the SKU from Module 1
2. **Geolocate** and **local time** supplied by the main BE (from its store data)
3. Query **Tavily** for news: `"news of <City> at <local date>"` and `"world news <local date>"`
4. Feed **consumption metrics + Tavily results** into an **LLM** (OpenAI-compatible: OpenAI, Ollama, LM Studio, Groq, etc.) for structured analysis:
   - `sentiment_score` -1 to +1
   - `demand_adjustment` multiplier (0.7–1.5)
   - `confidence_adjustment` extra margin (0.0–0.15)
   - `affected_categories` — which product categories are impacted
   - `explanation` — plain English summary (powers Module 7 Explain Why)
   - `action_window_days` — urgency hint
5. If LLM is unavailable, falls back to keyword heuristic
6. Apply trend adjustment based on recent velocity change
7. Apply seasonality/promotion uplift factors for the forecast horizon
8. Apply **news-context adjustment** from LLM analysis
9. Net out any incoming shipments already scheduled
10. Output a projected stock-out date with a confidence range, **news_context**, and **news analysis explanation**

## Config

- Forecast horizon (e.g. 7 / 14 / 30 days)
- Promotion uplift assumptions per category (editable by category manager)
- Trend sensitivity (how much weight recent days get vs. long-run average)
- Minimum data history required before a SKU is eligible for AI forecasting (fallback to simple average otherwise)
- `TAVILY_API_KEY` — API key for Tavily news search
- News weight factor (how much news signals influence the confidence interval)

## Insights

- A naive calculation (500 units / 22 per day ≈ 22.7 days) ignores an upcoming promotion
- Once a promotion starting in 3 days is factored in, consumption jumps from 22/day to 61/day
- The AI-adjusted forecast can shorten the stock-out estimate from ~23 days to 9 days — a materially different action window
- **News-aware forecasting** catches external events (e.g. typhoon warnings in Hanoi, global chip shortages) that internal data alone cannot predict

## Output

- A Forecast record: projected_stockout_date, confidence_low_date, confidence_high_date, trend_factor, promotion_uplift_pct, computed_at
- **news_context**: list of relevant news headlines with sentiment scores used in the adjustment
- Persisted to the forecasts table, linked back to the source consumption_profile_id
- Consumed by Module 3 (Reorder), Module 7 (Explain Why), Module 11 (Daily Report), Module 12 (Strategy Engine)

## Benefits

- Catches stock-outs that a simple average calculation would miss entirely
- Gives category managers lead time to react before, not after, a promotion drains stock
- Reduces both emergency stock-outs and unnecessary early reorders
- **News integration** provides early warning of external demand shocks not visible in POS data alone

## Integration

- Consumes Module 1's Consumption Profile as input
- Reads promotion calendar from the marketing/CRM system
- Reads open purchase orders from the procurement system
- **Queries Tavily API** for geo-localized and world news at forecast time
- Feeds forecast dates into Modules 3 (Reorder), 7 (Explain Why), 11 (Daily Report), 12 (Strategy Engine)

## Use Cases

- A category manager is planning a flash sale and needs to know if stock will hold
- Operations wants an early-warning list of SKUs likely to stock out this month
- Finance wants to compare forecast accuracy against actual outcomes over time
- **Supply chain manager** wants to know if a reported port strike or weather event will affect inbound shipments

## Business Value

- Converts a static inventory count into a forward-looking risk signal
- Reduces lost sales from unplanned stock-outs during promotions
- Builds trust in the system as forecast accuracy is tracked and improved over time
- **News-aware adjustments** reduce surprise stock-outs from external events by 20–30% (projected)