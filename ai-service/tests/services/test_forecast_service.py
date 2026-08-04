"""Tests for the news-aware ForecastService with LLM integration."""

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.forecast import ForecastResponse, NewsAnalysisResult
from app.services.forecast_service import ForecastService


def test_forecast_fallback_no_data(db_session):
    """When no consumption history exists, service falls back to defaults."""
    service = ForecastService(db_session)
    result = service.forecast(
        product_id="00000000-0000-0000-0000-000000000001",
        store_id="00000000-0000-0000-0000-000000000002",
        horizon_days=7,
    )
    assert isinstance(result, ForecastResponse)
    assert len(result.forecast) == 7
    assert result.model_used == "historical_ma"
    assert result.geolocate is None
    assert result.news_context is None


def test_forecast_with_geolocate_no_keys(db_session):
    """When caller supplies geolocate but no API keys, no news fetch."""
    service = ForecastService(db_session)
    result = service.forecast(
        product_id="00000000-0000-0000-0000-000000000001",
        store_id="00000000-0000-0000-0000-000000000002",
        horizon_days=5,
        geolocate="Hanoi, Vietnam",
        localtime="2026-07-17T10:00:00+07:00",
    )
    assert result.geolocate == "Hanoi, Vietnam"
    assert result.localtime is not None
    assert result.news_context is None
    assert result.model_used == "historical_ma"


@patch("app.services.forecast_service.settings")
def test_forecast_tavily_only_fallback(mock_settings, db_session):
    """Tavily key set but no LLM key → uses keyword heuristic fallback."""
    mock_settings.tavily_api_key = "test-tavily-key"
    mock_settings.llm_api_key = ""  # No LLM

    service = ForecastService(db_session)
    mock_tavily = MagicMock()
    mock_tavily.search.return_value = {
        "results": [
            {
                "title": "Typhoon warning in Hanoi",
                "url": "https://example.com/typhoon",
                "published_date": "2026-07-17",
                "content": "A strong typhoon is approaching Hanoi causing supply chain disruptions.",
            },
        ]
    }
    service._tavily_client = mock_tavily

    result = service.forecast(
        product_id="00000000-0000-0000-0000-000000000001",
        store_id="00000000-0000-0000-0000-000000000002",
        horizon_days=5,
        geolocate="Hanoi, Vietnam",
        localtime="2026-07-17T10:00:00+07:00",
    )

    assert result.model_used == "news_fallback"
    assert result.news_context is not None
    assert len(result.news_context) == 1
    assert result.news_sentiment_score is not None
    assert result.news_sentiment_score < 0  # Typhoon = negative
    assert result.news_adjustment_factor is not None
    assert result.news_adjustment_factor > 1.0  # Negative → demand spike


@patch("app.services.forecast_service.settings")
def test_forecast_llm_analysis(mock_settings, db_session):
    """Both Tavily and LLM keys set → uses LLM for analysis."""
    mock_settings.tavily_api_key = "test-tavily-key"
    mock_settings.llm_api_key = "test-llm-key"
    mock_settings.llm_base_url = "https://api.openai.com/v1"
    mock_settings.llm_model = "gpt-4o-mini"

    service = ForecastService(db_session)

    # Mock Tavily
    mock_tavily = MagicMock()
    mock_tavily.search.return_value = {
        "results": [
            {
                "title": "Typhoon warning in Hanoi",
                "url": "https://example.com/typhoon",
                "published_date": "2026-07-17",
                "content": "A strong typhoon is approaching Hanoi causing supply chain disruptions.",
            },
        ]
    }
    service._tavily_client = mock_tavily

    # Mock LLM
    mock_llm = MagicMock()
    mock_llm.structured_json.return_value = {
        "sentiment_score": -0.6,
        "demand_adjustment": 1.18,
        "confidence_adjustment": 0.08,
        "affected_categories": ["Accessory", "Smartphone"],
        "explanation": "Typhoon warning in Hanoi may cause supply disruptions, increasing demand for accessories and smartphones by ~18%.",
        "action_window_days": 3,
    }
    service._llm_client = mock_llm

    result = service.forecast(
        product_id="00000000-0000-0000-0000-000000000001",
        store_id="00000000-0000-0000-0000-000000000002",
        horizon_days=5,
        geolocate="Hanoi, Vietnam",
        localtime="2026-07-17T10:00:00+07:00",
    )

    assert result.model_used == "news_llm"
    assert result.news_context is not None
    assert len(result.news_context) == 1
    assert result.news_sentiment_score == -0.6
    assert result.news_adjustment_factor == 1.18

    # Verify LLM was called with consumption + news context
    mock_llm.structured_json.assert_called_once()
    call_kwargs = mock_llm.structured_json.call_args[1]
    assert "Hanoi" in call_kwargs["user_prompt"]
    assert "Typhoon" in call_kwargs["user_prompt"]
    assert "consumption" in call_kwargs["user_prompt"].lower()


@patch("app.services.forecast_service.settings")
def test_forecast_llm_failure_fallback(mock_settings, db_session):
    """LLM fails → falls back to keyword heuristic."""
    mock_settings.tavily_api_key = "test-tavily-key"
    mock_settings.llm_api_key = "test-llm-key"

    service = ForecastService(db_session)

    mock_tavily = MagicMock()
    mock_tavily.search.return_value = {
        "results": [
            {
                "title": "Typhoon warning in Hanoi",
                "url": "https://example.com/typhoon",
                "published_date": "2026-07-17",
                "content": "A strong typhoon is approaching Hanoi.",
            },
        ]
    }
    service._tavily_client = mock_tavily

    # LLM returns None (failure)
    mock_llm = MagicMock()
    mock_llm.structured_json.return_value = None
    service._llm_client = mock_llm

    result = service.forecast(
        product_id="00000000-0000-0000-0000-000000000001",
        store_id="00000000-0000-0000-0000-000000000002",
        horizon_days=5,
        geolocate="Hanoi, Vietnam",
        localtime="2026-07-17T10:00:00+07:00",
    )

    assert result.model_used == "news_fallback"
    assert result.news_sentiment_score < 0  # Fallback still catches typhoon


def test_heuristic_sentiment_aggregate():
    """Keyword heuristic correctly aggregates sentiment."""
    news = [
        {"title": "Supply chain disruption", "content": "Major shortage crisis"},
        {"title": "Festival season", "content": "Strong growth expected"},
    ]
    score = ForecastService._heuristic_sentiment_aggregate(news)
    # One negative, one positive → near zero
    assert -0.1 < score < 0.1


def test_heuristic_sentiment_aggregate_empty():
    """Empty news list → zero sentiment."""
    assert ForecastService._heuristic_sentiment_aggregate([]) == 0.0


def test_news_adjustment_negative():
    adj = ForecastService._compute_news_adjustment(-0.5)
    assert adj > 1.0


def test_news_adjustment_positive():
    adj = ForecastService._compute_news_adjustment(0.4)
    assert 1.0 < adj < 1.2


def test_news_adjustment_neutral():
    adj = ForecastService._compute_news_adjustment(0.0)
    assert adj == 1.0


def test_news_uncertainty_margin():
    assert ForecastService._news_uncertainty_margin(-0.6) == 0.10
    assert ForecastService._news_uncertainty_margin(0.35) == 0.05
    assert ForecastService._news_uncertainty_margin(0.1) == 0.0


def test_filter_news_context_items_threshold_and_cap():
    items = [
        MagicMock(title=f"Item {i}", relevance_score=score, url=f"https://example.com/{i}", published_date="2026-07-17")
        for i, score in enumerate([0.95, 0.85, 0.8, 0.75, 0.9, 0.99, 0.5, 0.88, 0.82, 0.7], start=1)
    ]
    filtered = ForecastService._filter_news_context_items(items)

    assert len(filtered) == 6
    assert all(item.relevance_score > 0.8 for item in filtered)
    assert filtered[0].relevance_score == 0.99
    assert filtered[-1].relevance_score == 0.82


def test_trend_computation():
    rising = [10.0, 12.0, 15.0, 18.0, 22.0]
    falling = [22.0, 18.0, 15.0, 12.0, 10.0]
    assert ForecastService._compute_trend(rising) > 0
    assert ForecastService._compute_trend(falling) < 0
    assert ForecastService._compute_trend([10.0]) == 0.0


def test_seasonality_computation(db_session):
    from app.models.consumption_profile import ConsumptionProfile

    today = date.today()
    profiles = []
    for i in range(14):
        d = today - timedelta(days=13 - i)
        qty = 200 if d.weekday() >= 5 else 100
        profile = ConsumptionProfile(
            product_id="00000000-0000-0000-0000-000000000001",
            store_id="00000000-0000-0000-0000-000000000002",
            date=d,
            quantity_sold=qty,
        )
        profiles.append(profile)

    seasonality = ForecastService._compute_seasonality(profiles)
    assert len(seasonality) == 7
    for dow, factor in seasonality.items():
        if dow >= 5:
            assert factor > 1.0, f"Expected weekend boost for day {dow}, got {factor}"
        else:
            assert factor < 1.0, f"Expected weekday discount for day {dow}, got {factor}"


def test_parse_geo_localtime():
    geo, dt = ForecastService._parse_geo_localtime(
        "Hanoi, Vietnam", "2026-07-17T10:00:00+07:00"
    )
    assert geo == "Hanoi, Vietnam"
    assert dt is not None
    assert dt.hour == 10


def test_parse_geo_localtime_none():
    geo, dt = ForecastService._parse_geo_localtime("Hanoi, Vietnam", None)
    assert geo == "Hanoi, Vietnam"
    assert dt is not None


def test_fallback_explanation():
    neg = ForecastService._fallback_explanation(-0.5, "Hanoi")
    pos = ForecastService._fallback_explanation(0.5, "Hanoi")
    neu = ForecastService._fallback_explanation(0.0, "Hanoi")
    assert "disruption" in neg
    assert "Positive" in pos
    assert "mixed" in neu