# AI Inventory Advisor Service

AI-powered inventory management microservice providing demand forecasting, reorder recommendations, overstock detection, and strategy generation.

## Architecture

```
ai-service/
├── app/
│   ├── main.py              # FastAPI entrypoint
│   ├── config.py            # Pydantic settings
│   ├── deps.py              # Shared dependencies
│   ├── api/v1/              # 12 REST endpoints (M1-M12)
│   ├── schemas/             # Pydantic v2 models
│   ├── services/            # Business logic (pandas/numpy/sklearn)
│   ├── models/              # SQLAlchemy models
│   ├── db/                  # Session + repositories
│   ├── batch/               # Nightly batch jobs
│   └── core/                # Errors, middleware, security
├── tests/
├── alembic/
├── Dockerfile
└── requirements.txt
```

## API Endpoints

| Module | Endpoint                            | Description              |
| ------ | ----------------------------------- | ------------------------ |
| M1     | `POST /api/v1/consumption/analyze`  | Consumption analysis     |
| M2     | `POST /api/v1/forecast`             | Demand forecast          |
| M3     | `POST /api/v1/reorder/recommend`    | Reorder recommendations  |
| M4     | `POST /api/v1/overstock/detect`     | Overstock detection      |
| M5     | `POST /api/v1/classify`             | ABC/XYZ classification   |
| M6     | `POST /api/v1/simulate`             | Monte Carlo simulation   |
| M7     | `POST /api/v1/explain`              | AI explanation           |
| M8     | `POST /api/v1/supplier/reliability` | Supplier reliability     |
| M9     | `POST /api/v1/transfer/recommend`   | Transfer recommendations |
| M10    | `POST /api/v1/chat`                 | Chat assistant           |
| M11    | `POST /api/v1/report/daily`         | Daily report             |
| M12    | `POST /api/v1/strategy/generate`    | Strategy generation      |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env

# Run the service
uvicorn app.main:app --reload

# Access API docs
open http://localhost:8000/docs
```

## Batch Jobs

```bash
# Run all nightly jobs in order
python -m app.batch.run_all

# Or run individual stages
python -m app.batch.run_foundation   # M1 + M8
python -m app.batch.run_analysis     # M2 + M5
python -m app.batch.run_decision     # M3 + M4 + M9
python -m app.batch.run_strategy     # M12 + M7
```

## Docker

```bash
docker build -t ai-inventory-advisor .
docker run -p 8000:8000 --env-file .env ai-inventory-advisor
```
