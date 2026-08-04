"""Demand forecast service — M2 logic with Tavily + LLM news analysis."""

import logging
import time
from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
from sqlalchemy.orm import Session
from tavily import TavilyClient

from app.config import settings
from app.core.llm import LLMClient
from app.db.repositories.consumption_repo import ConsumptionRepository
from app.db.repositories.forecast_repo import ForecastRepository
from app.schemas.forecast import (
    ForecastPoint,
    ForecastResponse,
    NewsAnalysisResult,
    NewsContextItem,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt used for every news analysis call.
# ---------------------------------------------------------------------------
NEWS_ANALYSIS_SYSTEM_PROMPT = """You are a retail inventory analyst. Your job is to analyze news articles
alongside consumption data to determine how local and world events may affect product demand at a specific store.

Only treat an article as relevant if it plausibly changes consumer purchasing behavior — e.g. festivals,
public holidays, major sporting events (World Cup finals, Olympics), product launches, promotions or sales
events, natural disasters, supply disruptions, strikes, or significant economic news (tariffs, inflation
shocks). Routine local news (crime, minor political stories, general-interest pieces) with no plausible
link to consumer demand should be ignored, not scored.

Return a JSON object with these fields:
- relevant_titles: list of article titles (copy the exact title text from the input) that materially affect
  demand. Omit any article that has no plausible effect on purchasing behavior — this list may be shorter
  than the input, or empty if nothing is relevant.
- sentiment_score: float between -1.0 (very negative) to +1.0 (very positive), based only on the relevant articles
- demand_adjustment: float multiplier to apply to baseline demand (1.0 = no change, 1.15 = +15% demand)
- confidence_adjustment: float extra uncertainty margin (0.0 = no change, 0.1 = widen bands by 10%)
- affected_categories: list of product category strings that may be impacted (e.g. ["Smartphone", "Laptop"]).
  Leave empty if the impact applies store-wide rather than to specific categories.
- explanation: 1-2 sentence plain English summary of the news impact
- action_window_days: integer or null — how many days from today the demand impact is concentrated in
  (e.g. 2 for a festival happening in 2 days with a short-lived spike, 14 for a slower-building holiday season)

Guidelines:
- Natural disasters, supply disruptions, strikes → negative sentiment, demand may spike (panic buying)
- Holidays, festivals, promotions, product launches, major sporting finals → positive sentiment, demand
  boost concentrated around the event date
- World events like chip shortages → affect specific categories (Laptop, Smartphone) — list them in affected_categories
- Local events like city-wide sales or festivals → affect all categories at that store — leave affected_categories empty
- Keep demand_adjustment between 0.7 and 1.5
- Set confidence_adjustment higher (0.05–0.15) when news is uncertain or contradictory
- Set action_window_days to 0 if impact is immediate/ongoing, or to the number of days until a known upcoming event"""

# ---------------------------------------------------------------------------
# Keyword sets used by the no-LLM heuristic fallback (sentiment + relevance).
# Pulled out as class-level constants so both scoring and relevance filtering
# can share them.
# ---------------------------------------------------------------------------
NEGATIVE_KEYWORDS = [
    "shortage", "disruption", "delay", "crisis", "strike",
    "typhoon", "flood", "earthquake", "pandemic", "lockdown",
    "tariff", "sanction", "inflation", "recession", "bankrupt",
    "recall", "defect", "shortfall", "outage", "collapse",
]

POSITIVE_KEYWORDS = [
    "growth", "boom", "expansion", "stimulus", "subsidy",
    "festival", "holiday", "celebration", "launch", "release",
    "investment", "infrastructure", "recovery", "rebound",
    "incentive", "discount", "sale", "promotion",
]

# Event-type keywords that signal demand relevance even without clear
# positive/negative sentiment — these are what were previously missing and
# causing generic news to swamp the actually-useful signal.
EVENT_KEYWORDS = [
    "world cup", "olympics", "championship", "final", "tournament",
    "christmas", "new year", "black friday", "cyber monday",
    "concert", "carnival", "parade", "national day", "public holiday",
]

# Tavily result cache: (city_lower, date_str) -> (fetched_at, items, raw).
# In-process only — fine for a single worker, but won't be shared across
# multiple workers/replicas. Swap for Redis if that matters for deployment.
_TAVILY_CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours
_tavily_cache: dict[tuple[str, str], tuple[float, list, list]] = {}


class ForecastService:
    """Generates demand forecasts with real-world news context.

    Flow:
      1. Pull real consumption data from Module 1 (ConsumptionProfile).
      2. Accept geolocate + localtime from the caller (the main BE).
      3. Query Tavily for local + world events likely to affect demand.
      4. Feed consumption metrics + Tavily results into an LLM for structured analysis.
      5. Apply the LLM's demand_adjustment, confidence_adjustment, and action_window.
      6. Build forecast points with trend, seasonality, and news adjustments.
      7. Return forecast with news_context and explanation (for M7).
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.consumption_repo = ConsumptionRepository(db)
        self.forecast_repo = ForecastRepository(db)
        self._tavily_client: TavilyClient | None = None
        self._llm_client: LLMClient | None = None

    # ------------------------------------------------------------------
    # Tavily client (lazy-init)
    # ------------------------------------------------------------------
    @property
    def tavily(self) -> TavilyClient | None:
        if self._tavily_client is None and settings.tavily_api_key:
            self._tavily_client = TavilyClient(api_key=settings.tavily_api_key)
        return self._tavily_client

    # ------------------------------------------------------------------
    # LLM client (lazy-init)
    # ------------------------------------------------------------------
    @property
    def llm(self) -> LLMClient | None:
        if self._llm_client is None and settings.llm_api_key:
            self._llm_client = LLMClient()
        return self._llm_client

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def forecast(
        self,
        product_id: Any,
        store_id: Any,
        horizon_days: int = 30,
        geolocate: str | None = None,
        localtime: str | None = None,
        product_category: str | None = None,
    ) -> ForecastResponse:
        # 1. Pull real consumption data (Module 1 output)
        end = date.today()
        start = end - timedelta(days=90)
        profiles = self.consumption_repo.get_by_product_store(
            product_id, store_id, start, end
        )

        # 2. Compute base consumption metrics
        base_daily, trend, seasonality, consumption_summary = self._compute_consumption_metrics(profiles)

        # 3. Parse caller-supplied geolocate + localtime
        geo, local_dt = self._parse_geo_localtime(geolocate, localtime)

        # 4. Query Tavily for demand-relevant events
        tavily_items, news_context = self._fetch_news(geo, local_dt)

        # 5. Analyze news with LLM
        analysis, relevant_titles = self._analyze_news_with_llm(
            consumption_summary, news_context, geo
        )

        # 6. Resolve final adjustment values (LLM result or fallback)
        demand_adj = 1.0
        conf_adj = 0.0
        explanation = ""
        action_window_days: int | None = None

        if analysis is not None:
            demand_adj = analysis.demand_adjustment
            conf_adj = analysis.confidence_adjustment
            explanation = analysis.explanation
            action_window_days = analysis.action_window_days

            # NEW: only apply a category-specific adjustment to a product
            # that's actually in an affected category. Store-wide news
            # (empty affected_categories) still applies to everything.
            if analysis.affected_categories and product_category:
                category_matches = False
                for cat in analysis.affected_categories:
                    if cat.strip().lower() == product_category.strip().lower():
                        category_matches = True
                        break
                if not category_matches:
                    demand_adj = 1.0
                    conf_adj = 0.0
                    action_window_days = None

            # NEW: keep only the news items the LLM judged relevant.
            tavily_items = self._apply_llm_relevance(tavily_items, relevant_titles)

        elif news_context:
            # LLM unavailable but we have news — use keyword heuristic as fallback
            sentiment = self._heuristic_sentiment_aggregate(news_context)
            demand_adj = self._compute_news_adjustment(sentiment)
            conf_adj = self._news_uncertainty_margin(sentiment)
            explanation = self._fallback_explanation(sentiment, geo)
            # NEW: same relevance filtering, done via keywords instead of the LLM.
            tavily_items = self._apply_heuristic_relevance(tavily_items)

        # 7. Build forecast points
        points: list[ForecastPoint] = []
        base_margin = 0.15
        margin = base_margin + conf_adj

        for i in range(horizon_days):
            d = end + timedelta(days=i)
            trend_ramp = 1.0 + (trend * i / horizon_days)
            day_seasonality = self._day_seasonality(d, seasonality)

            # NEW: taper the news adjustment around action_window_days instead
            # of applying it flat across the whole horizon. Days inside the
            # window get the full adjustment; days after it decay linearly
            # back to neutral over a short tail so the curve doesn't snap.
            day_demand_adj = self._windowed_demand_adjustment(
                day_index=i, demand_adj=demand_adj, action_window_days=action_window_days
            )

            pred = base_daily * day_seasonality * trend_ramp * day_demand_adj

            noise = float(np.random.normal(0, pred * 0.05))
            pred = max(0.0, pred + noise)

            points.append(
                ForecastPoint(
                    date=d,
                    predicted_quantity=round(pred, 2),
                    lower_bound=round(pred * (1.0 - margin), 2),
                    upper_bound=round(pred * (1.0 + margin), 2),
                )
            )

        model_used = "historical_ma"
        if analysis is not None:
            model_used = "news_llm"
        elif news_context:
            model_used = "news_fallback"

        avg_sentiment = 0.0
        if analysis is not None:
            avg_sentiment = analysis.sentiment_score

        return ForecastResponse(
            product_id=product_id,
            store_id=store_id,
            forecast=points,
            model_used=model_used,
            confidence_level=round(1.0 - margin, 2),
            geolocate=geo,
            localtime=local_dt.isoformat() if local_dt else None,
            news_context=tavily_items if tavily_items else None,
            news_sentiment_score=round(avg_sentiment, 4) if news_context else None,
            news_adjustment_factor=round(demand_adj, 4) if news_context else None,
        )

    # ======================================================================
    # Consumption metrics
    # ======================================================================
    def _compute_consumption_metrics(self, profiles):
        """Return (base_daily, trend, seasonality_dict, summary_string)."""
        if profiles:
            quantities = [p.quantity_sold for p in profiles]
            base_daily = float(np.mean(quantities))
            trend = self._compute_trend(quantities)
            seasonality = self._compute_seasonality(profiles)
            summary = (
                f"Average daily sales: {base_daily:.1f} units. "
                f"Trend: {trend:+.4f} per day. "
                f"Days of history: {len(quantities)}."
            )
        else:
            base_daily = 100.0
            trend = 0.0
            seasonality = {}
            summary = "No historical data available. Using default baseline."
        return base_daily, trend, seasonality, summary

    # ======================================================================
    # Trend
    # ======================================================================
    @staticmethod
    def _compute_trend(quantities: list[float]) -> float:
        if len(quantities) < 2:
            return 0.0
        x = np.arange(len(quantities))
        y = np.array(quantities)
        slope = np.polyfit(x, y, 1)[0]
        mean_y = float(np.mean(y))
        if mean_y == 0:
            return 0.0
        return float(np.clip(slope / mean_y, -0.1, 0.1))

    # ======================================================================
    # Seasonality
    # ======================================================================
    @staticmethod
    def _compute_seasonality(profiles) -> dict[int, float]:
        dow_sums: dict[int, float] = {}
        dow_counts: dict[int, int] = {}
        for p in profiles:
            if p.date is None:
                continue
            dow = p.date.weekday()
            dow_sums[dow] = dow_sums.get(dow, 0.0) + p.quantity_sold
            dow_counts[dow] = dow_counts.get(dow, 0) + 1
        if not dow_counts:
            return {}
        overall_avg = sum(dow_sums.values()) / sum(dow_counts.values())
        if overall_avg == 0:
            return {}
        return {
            dow: (dow_sums[dow] / dow_counts[dow]) / overall_avg
            for dow in dow_sums
        }

    @staticmethod
    def _day_seasonality(d: date, seasonality: dict[int, float]) -> float:
        return seasonality.get(d.weekday(), 1.0)

    # ======================================================================
    # NEW: apply action_window_days to the forecast curve
    # ======================================================================
    @staticmethod
    def _windowed_demand_adjustment(
        day_index: int,
        demand_adj: float,
        action_window_days: int | None,
        decay_tail_days: int = 3,
    ) -> float:
        """Shape demand_adj across the horizon instead of applying it flat.

        - If action_window_days is None, apply demand_adj uniformly (old
          behavior — used when we have no window info, e.g. plain historical
          fallback).
        - If day_index is within the window, apply the full adjustment.
        - For a few days after the window, linearly decay back to neutral
          (1.0) so the curve doesn't snap abruptly at the boundary.
        - Beyond the decay tail, demand returns to neutral (1.0).
        """
        if action_window_days is None:
            return demand_adj

        if day_index <= action_window_days:
            return demand_adj

        days_past_window = day_index - action_window_days
        if days_past_window <= decay_tail_days:
            decay_fraction = 1.0 - (days_past_window / decay_tail_days)
            return 1.0 + (demand_adj - 1.0) * decay_fraction

        return 1.0

    # ======================================================================
    # Geo/time parsing
    # ======================================================================
    @staticmethod
    def _parse_geo_localtime(
        geolocate: str | None, localtime: str | None
    ) -> tuple[str | None, datetime | None]:
        local_dt: datetime | None = None
        if localtime:
            try:
                local_dt = datetime.fromisoformat(localtime)
            except (ValueError, TypeError):
                pass
        if local_dt is None:
            local_dt = datetime.utcnow()
        return geolocate, local_dt

    # ======================================================================
    # Tavily news fetch
    # ======================================================================
    def _fetch_news(
        self, geo: str | None, local_dt: datetime | None
    ) -> tuple[list[NewsContextItem] | None, list[dict[str, str]]]:
        """Query Tavily for demand-relevant local + world events.

        Returns (NewsContextItem list for response, raw context dicts for LLM).
        """
        client = self.tavily
        if client is None or not geo or local_dt is None:
            return None, []

        local_date_str = local_dt.strftime("%Y-%m-%d")
        city = geo.split(",")[0].strip()

        # NEW: cache hit avoids repeat Tavily calls for the same store/day
        # when forecasting several products back to back.
        cache_key = (city.lower(), local_date_str)
        cached = _tavily_cache.get(cache_key)
        if cached is not None:
            cached_at, cached_items, cached_raw = cached
            if time.time() - cached_at < _TAVILY_CACHE_TTL_SECONDS:
                return cached_items, cached_raw

        # NEW: split into targeted, forward-looking queries instead of one
        # generic "news of {city}" query. This is what was returning noise —
        # routine local news with no bearing on demand.
        queries = [
            f"upcoming festivals holidays events in {city} near {local_date_str}",
            f"major sporting events tournaments finals {local_date_str}",
            f"supply chain disruption shortage strike {local_date_str}",
        ]
        seen_titles: set[str] = set()
        items: list[NewsContextItem] = []
        raw: list[dict[str, str]] = []

        for query in queries:
            try:
                result = client.search(
                    query=query,
                    search_depth="basic",
                    max_results=4,
                    include_raw_content=False,
                )
                for r in (result.get("results") or []):
                    title = (r.get("title") or "").strip()
                    if not title or title in seen_titles:
                        continue
                    seen_titles.add(title)
                    content = r.get("content") or ""
                    items.append(
                        NewsContextItem(
                            title=title,
                            url=r.get("url"),
                            published_date=r.get("published_date"),
                            relevance_score=0.5,  # placeholder — set for real in _apply_*_relevance
                        )
                    )
                    # Bumped from 500 to 800 chars — event dates/details were
                    # sometimes getting truncated out before reaching the LLM.
                    raw.append({"title": title, "content": content[:800]})
            except Exception:
                logger.warning("Tavily search failed for query: %s", query, exc_info=True)

        final_items = items if items else None
        _tavily_cache[cache_key] = (time.time(), final_items, raw)
        return final_items, raw

    # ======================================================================
    # NEW: relevance filtering
    # ======================================================================
    @staticmethod
    def _apply_llm_relevance(
        items: list[NewsContextItem] | None,
        relevant_titles: set[str],
    ) -> list[NewsContextItem] | None:
        """Keep only the articles the LLM judged demand-relevant.

        Falls back to returning all items unfiltered if none of the titles
        matched (e.g. the LLM paraphrased a title) so a matching miss
        doesn't silently drop everything.
        """
        if not items:
            return items
        if not relevant_titles:
            return items

        filtered = []
        for item in items:
            if item.title in relevant_titles:
                item.relevance_score = 1.0
                filtered.append(item)

        if filtered:
            return filtered
        return items

    @staticmethod
    def _apply_heuristic_relevance(
        items: list[NewsContextItem] | None,
    ) -> list[NewsContextItem] | None:
        """Keyword-based relevance filter for the no-LLM fallback path."""
        if not items:
            return items

        all_keywords = NEGATIVE_KEYWORDS + POSITIVE_KEYWORDS + EVENT_KEYWORDS
        filtered = []
        for item in items:
            text = (item.title or "").lower()
            is_relevant = False
            for kw in all_keywords:
                if kw in text:
                    is_relevant = True
                    break
            if is_relevant:
                item.relevance_score = 0.7
                filtered.append(item)

        if filtered:
            return filtered
        return items

    # ======================================================================
    # LLM news analysis
    # ======================================================================
    def _analyze_news_with_llm(
        self,
        consumption_summary: str,
        news_context: list[dict[str, str]],
        geo: str | None,
    ) -> tuple[NewsAnalysisResult | None, set[str]]:
        """Feed consumption + news into LLM, return structured analysis plus
        the set of article titles the LLM judged actually relevant to demand."""
        llm_client = self.llm
        if llm_client is None or not news_context:
            return None, set()

        # Build user prompt
        articles_text = "\n\n".join(
            f"Title: {a['title']}\nContent: {a['content']}"
            for a in news_context
        )
        user_prompt = (
            f"Store location: {geo or 'Unknown'}\n\n"
            f"Consumption data:\n{consumption_summary}\n\n"
            f"News articles:\n{articles_text}\n\n"
            "Analyze how these news events might affect product demand at this store."
        )

        raw = llm_client.structured_json(
            system_prompt=NEWS_ANALYSIS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        if raw is None:
            return None, set()

        relevant_titles = set(raw.get("relevant_titles") or [])

        try:
            analysis = NewsAnalysisResult(
                sentiment_score=float(raw.get("sentiment_score", 0.0)),
                demand_adjustment=float(raw.get("demand_adjustment", 1.0)),
                confidence_adjustment=float(raw.get("confidence_adjustment", 0.0)),
                affected_categories=raw.get("affected_categories") or [],
                explanation=raw.get("explanation") or "",
                action_window_days=raw.get("action_window_days"),
            )
        except (ValueError, TypeError) as exc:
            logger.warning("Failed to parse LLM output: %s — raw: %s", exc, raw)
            return None, set()

        return analysis, relevant_titles

    # ======================================================================
    # Fallback heuristic (when LLM is unavailable)
    # ======================================================================
    @staticmethod
    def _heuristic_sentiment_aggregate(news_context: list[dict[str, str]]) -> float:
        """Aggregate keyword sentiment across all news items."""
        if not news_context:
            return 0.0
        scores = []
        for item in news_context:
            text = (item.get("title", "") + " " + item.get("content", "")).lower()
            score = 0.0
            for kw in NEGATIVE_KEYWORDS:
                if kw in text:
                    score -= 0.15
            for kw in POSITIVE_KEYWORDS:
                if kw in text:
                    score += 0.12
            scores.append(float(np.clip(score, -1.0, 1.0)))
        return float(np.mean(scores)) if scores else 0.0

    @staticmethod
    def _compute_news_adjustment(sentiment_score: float) -> float:
        if sentiment_score < -0.3:
            return 1.0 + (abs(sentiment_score) * 0.3)
        elif sentiment_score < 0:
            return 1.0 + (abs(sentiment_score) * 0.1)
        elif sentiment_score > 0.3:
            return 1.0 + (sentiment_score * 0.15)
        elif sentiment_score > 0:
            return 1.0 + (sentiment_score * 0.05)
        return 1.0

    @staticmethod
    def _news_uncertainty_margin(sentiment_score: float) -> float:
        extremity = abs(sentiment_score)
        if extremity > 0.5:
            return 0.10
        elif extremity > 0.3:
            return 0.05
        return 0.0

    @staticmethod
    def _fallback_explanation(sentiment: float, geo: str | None) -> str:
        if sentiment < -0.3:
            return f"News from {geo or 'the region'} indicates potential supply disruption, raising demand estimates."
        elif sentiment > 0.3:
            return f"Positive news from {geo or 'the region'} suggests increased consumer activity."
        return f"News from {geo or 'the region'} shows mixed signals — minimal adjustment applied."