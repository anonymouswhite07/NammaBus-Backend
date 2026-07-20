# Namma Bus Backend Gateway

A production-ready, high-performance transit tracking API gateway built using **FastAPI**, **SQLAlchemy 2.0**, **PostgreSQL**, **Redis**, and **Docker**.

---

## 🛠️ Technology Stack

- **Core Framework**: FastAPI (Async ASGI)
- **Database**: PostgreSQL 16 (Relational database with UUID keys & Soft-deletes)
- **ORM & Sessions**: SQLAlchemy 2.0 (declarative async mappings)
- **Data Migrations**: Alembic
- **Caching**: Redis
- **Authentication**: JWT access/refresh token rotation + Firebase Token mapping
- **Realtime**: WebSockets (Chat rooms, live bus tracking coordinates, instant alerts)
- **Inference**: Predictive Machine Learning pipelines (ETAs, crowds, dead reckoning)
- **Telemetry**: Structured JSON logs
- **DevOps**: Docker, Docker Compose

---

## 📁 Repository Structure

```
backend/
 ├── app/
 │    ├── api/                     # REST Router paths (v1 endpoints)
 │    │    ├── v1/
 │    │    │    ├── auth.py        # Login, Register, Firebase integration
 │    │    │    ├── buses.py       # Bus and operator fleet registry
 │    │    │    ├── routes.py      # Route planning and stop sequences
 │    │    │    ├── stops.py       # Station listings and GPS nearby range
 │    │    │    ├── timetable.py   # Scheduled routes (CSV bulk import/export)
 │    │    │    ├── reports.py     # Commuters location / crowd reports
 │    │    │    ├── favorites.py   # Commuters starred favorites
 │    │    │    ├── notifications.py # Inbox messages & FCM push alerts
 │    │    │    ├── ads.py         # Sponsors impressions and clicks logs
 │    │    │    ├── admin.py       # Dashboard statistics
 │    │    │    ├── analytics.py   # Delay metrics, peak hours
 │    │    │    └── ml.py          # ETA and crowd predictions
 │    │    └── router.py           # V1 endpoint aggregator
 │    ├── core/                    # Security configurations, loggers, rate limiters
 │    ├── config/                  # Settings configuration loader (Pydantic-Settings)
 │    ├── database/                # SQLAlchemy session lifecycle and Base model mixin
 │    ├── models/                  # SQLAlchemy 2.0 models
 │    ├── repositories/            # Async CRUD database transactions
 │    ├── schemas/                 # Pydantic V2 validations input/output
 │    ├── services/                # FCM notifications, Firebase verify services
 │    ├── websocket/               # WebSocket connections and routing managers
 │    │    ├── manager.py          # WebSocket client rooms manager
 │    │    ├── chat_ws.py          # WS Room Chat (/ws/chat/{route_id})
 │    │    ├── location_ws.py      # WS GPS Coordinates (/ws/location/{route_id})
 │    │    ├── notification_ws.py  # WS Live Alerts (/ws/notifications)
 │    │    └── admin_ws.py         # WS Admin Analytics (/ws/admin)
 │    └── ml/                      # Machine learning prediction pipelines
 │         └── services.py         # XGBoost and Kalman filters models mock
 │    └── main.py                  # ASGI Application bootstrap
 ├── migrations/                   # Alembic database migrations
 ├── alembic.ini                   # Alembic configuration
 ├── Dockerfile                    # Container configuration
 ├── docker-compose.yml            # PostgreSQL, Redis, and FastAPI composition
 ├── requirements.txt              # Production python packages
 └── README.md                     # Backend documentation
```

---

## ⚙️ Environment Variables (`.env`)

The system loads variables automatically. Create a `.env` file inside `backend/` with the following parameters:

```env
PROJECT_NAME="Namma Bus API"
SECRET_KEY="38a531bdfd70dc264a7ef19602a8bf3dcfcd3f9ad72a392ce818c39db5c54b2d"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
DATABASE_URL=postgresql+asyncpg://postgres:secret_password@db:5432/namma_bus
REDIS_URL=redis://redis:6379/0
FIREBASE_CREDENTIALS_PATH=/app/firebase-credentials.json
```

---

## 🚀 Deployment & Installation

### Local Setup
1. Clone repository and navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Create and activate a python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start FastAPI server locally:
   ```bash
   uvicorn app.main:app --reload
   ```

### Docker Deploy (Recommended)
Compile and launch PostgreSQL, Redis, and FastAPI in unified orchestration:
```bash
docker-compose up --build -d
```

Confirm health of services:
```bash
docker-compose ps
```

To view logs in real-time:
```bash
docker-compose logs -f
```

---

## 📖 API Documentation

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Testing

Execute Python test suites:
```bash
pytest
```
