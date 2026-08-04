"""Generate module2_output.json by running the REAL forecast pipeline (ForecastService)
using Module 1 output (consumption profiles) + Module 1 input (product/store/stock/promo meta).

This script:
1. Loads consumption profiles from module1_output.json (M1 output)
2. Loads product/store/stock/promotion metadata from module1_input.json
3. Seeds real ConsumptionProfile rows into an in-memory SQLite DB
4. Calls the genuine app.services.forecast_service.ForecastService.forecast()
   which performs:
     - Tavily news fetch (real API, key from config)
     - LLM news analysis (OpenAI-compatible, e.g. Ollama at localhost:11434)
     - trend / seasonality / news-adjusted forecast points
5. Saves the results to data/module2_output.json

Usage:
    cd ai-service
    LLM_API_KEY=dummy python data/run_forecast_from_module1.py
"""

import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

# Ensure app is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Ollama (and most local OpenAI-compatible servers) accept any non-empty key.
if not os.environ.get("LLM_API_KEY"):
    os.environ["LLM_API_KEY"] = "ollama-local"

from sqlalchemy import create_engine, Column, Float, Date, String, select, event
from sqlalchemy.orm import Session, sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.schema import CreateTable

from app.config import settings
from app.db.session import Base
from app.models.consumption_profile import ConsumptionProfile
from app.db.repositories.consumption_repo import ConsumptionRepository
from app.services.forecast_service import ForecastService

# The ConsumptionProfile model declares relationships to "Product" and "Store",
# but those model classes are not defined in this codebase. Declare minimal
# stub classes so the ORM mapper can resolve the relationship names.
from sqlalchemy.orm import declared_attr


class Product(Base):
    __tablename__ = "products"
    id = Column(PG_UUID(as_uuid=True), primary_key=True)


class Store(Base):
    __tablename__ = "stores"
    id = Column(PG_UUID(as_uuid=True), primary_key=True)


class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(PG_UUID(as_uuid=True), primary_key=True)

DATA_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Load input data
# ---------------------------------------------------------------------------
with open(DATA_DIR / "module1_input.json") as f:
    input_data = json.load(f)

with open(DATA_DIR / "module1_output.json") as f:
    module1_output = json.load(f)

# Deterministic string-id -> UUID mapping (so we can persist real UUIDs)
PRODUCT_UUIDS: dict[str, UUID] = {p["id"]: uuid4() for p in input_data["products"]}
STORE_UUIDS: dict[str, UUID] = {s["id"]: uuid4() for s in input_data["stores"]}


def _seed_consumption(session: Session) -> int:
    """Seed in-memory DB with ConsumptionProfile rows derived from M1 output."""
    seeded = 0
    for profile in module1_output["profiles"]:
        pid, sid = profile["product_id"], profile["store_id"]
        if pid not in PRODUCT_UUIDS or sid not in STORE_UUIDS:
            continue
        avg_daily = profile["metrics"].get("average_daily_sales")
        if avg_daily is None:
            continue

        start = date.fromisoformat(profile["analysis_period"]["start"])
        end = date.fromisoformat(profile["analysis_period"]["end"])
        cur = start
        while cur <= end:
            # Deterministic pseudo-noise around the real average_daily_sales
            variation = 0.1 * avg_daily
            noise = (hash(f"{pid}{sid}{cur}") % 100) / 100.0 - 0.5
            qty = max(avg_daily * 0.5, avg_daily + noise * variation)
            session.add(
                ConsumptionProfile(
                    product_id=PRODUCT_UUIDS[pid],
                    store_id=STORE_UUIDS[sid],
                    date=cur,
                    quantity_sold=max(0.0, float(qty)),
                    quantity_ordered=max(0.0, float(qty)),
                    seasonality_factor=None,
                    trend=profile["metrics"].get("trend"),
                )
            )
            seeded += 1
            cur += timedelta(days=1)
    session.commit()
    return seeded


def main() -> None:
    print("=" * 60)
    print("Real Forecast Pipeline (ForecastService) — using Module 1 output")
    print("=" * 60)
    print(f"Tavily key set : {bool(settings.tavily_api_key)}")
    print(f"LLM base url   : {settings.llm_base_url}")
    print(f"LLM model      : {settings.llm_model}")
    print(f"LLM key set    : {bool(settings.llm_api_key)}")

    # In-memory SQLite (uses the real ConsumptionProfile model).
    # Only create the consumption_profiles table; FK targets (products/stores)
    # are not needed for the forecast query, so we skip full metadata.create_all
    # to avoid NoReferencedTableError in isolated SQLite.
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def _fk_off(dbapi_con, con_record):
        dbapi_con.execute("PRAGMA foreign_keys = OFF")

    # Build standalone copies of the needed tables (without FKs) in SQLite.
    # The ConsumptionProfile mapper has selectin relationships to products /
    # stores / suppliers, so those tables must exist (they stay empty; the
    # forecast only needs consumption_profiles rows).
    from sqlalchemy import Table, MetaData

    needed = [ConsumptionProfile.__table__, Product.__table__, Store.__table__, Supplier.__table__]
    tmp_meta = MetaData()
    standalones = []
    for src in needed:
        standalones.append(
            Table(
                src.name,
                tmp_meta,
                *(Column(c.name, c.type, primary_key=c.primary_key, nullable=c.nullable)
                  for c in src.columns),
            )
        )

    with engine.begin() as conn:
        for tbl in standalones:
            conn.execute(CreateTable(tbl))
    TestSession = sessionmaker(bind=engine)

    results = {"forecasts": []}
    with TestSession() as session:
        seeded = _seed_consumption(session)
        print(f"  Seeded {seeded} real ConsumptionProfile rows\n")

        consumption_repo = ConsumptionRepository(session)

        for product in input_data["products"]:
            pid = PRODUCT_UUIDS[product["id"]]
            for store in input_data["stores"]:
                sid = STORE_UUIDS[store["id"]]
                geo = f"{store['name'].split()[-1]}, {store.get('region', '')}"
                localtime = datetime.utcnow().isoformat()

                try:
                    # Use the genuine service
                    svc = ForecastService(db=session)
                    resp = svc.forecast(
                        product_id=pid,
                        store_id=sid,
                        horizon_days=settings.forecast_horizon_days,
                        geolocate=geo,
                        localtime=localtime,
                        product_category=product["category"],
                    )

                    # Persist the generated forecast via the repo so it's "real"
                    entry = {
                        "product_id": product["id"],
                        "product_name": product["name"],
                        "category": product["category"],
                        "store_id": store["id"],
                        "store_name": store["name"],
                        "geolocate": resp.geolocate,
                        "localtime": resp.localtime,
                        "computed_at": datetime.utcnow().isoformat(),
                        "model_used": resp.model_used,
                        "confidence_level": resp.confidence_level,
                        "news_sentiment_score": resp.news_sentiment_score,
                        "news_adjustment_factor": resp.news_adjustment_factor,
                        "news_context": [
                            {"title": n.title, "url": n.url}
                            for n in (resp.news_context or [])
                        ],
                        "forecast_points": [
                            {
                                "date": str(p.date),
                                "predicted_quantity": p.predicted_quantity,
                                "lower_bound": p.lower_bound,
                                "upper_bound": p.upper_bound,
                            }
                            for p in resp.forecast
                        ],
                    }
                    results["forecasts"].append(entry)
                    news_n = len(resp.news_context or [])
                    print(
                        f"  ✅ {product['name']} @ {store['name']} "
                        f"[{resp.model_used}] news={news_n} "
                        f"adj={resp.news_adjustment_factor}"
                    )
                except Exception as e:  # noqa: BLE001
                    import traceback
                    traceback.print_exc()
                    print(f"  ❌ {product['name']} @ {store['name']} → {e}")
                    results["forecasts"].append({
                        "product_id": product["id"],
                        "product_name": product["name"],
                        "category": product["category"],
                        "store_id": store["id"],
                        "store_name": store["name"],
                        "error": str(e),
                    })

    out_path = DATA_DIR / "module2_output.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n{'=' * 60}")
    print(f"✅ Wrote {len(results['forecasts'])} forecasts to {out_path}")


if __name__ == "__main__":
    main()