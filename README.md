# FakeScope Backend — API-only (no browser needed for deployment)
fakescope-backend/
├── main.py          ← FastAPI app + all routes
├── .env             ← ANTHROPIC_API_KEY (never commit this)
└── requirements.txt ← pinned deps for Render

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run locally

```bash
uvicorn main:app --reload
```

Swagger UI → http://localhost:8000/docs

## Routes

| Method | Path          | Description                        |
|--------|---------------|------------------------------------|
| POST   | /check-text   | Analyze text for scam indicators   |
| GET    | /health       | Health check                       |

## JSON Contract (shared with P1 frontend & P3 image/deepfake)

```json
{
  "danger_score": 0,
  "type": "scam|safe",
  "scam_category": "credit_card|kyc|crypto|lottery|job_fraud|safe",
  "red_flags": ["flag1", "flag2"],
  "explanation": "1-2 lines, simple language",
  "precautions": ["action1", "action2"],
  "block_recommended": true,
  "report_to": "cybercrime.gov.in"
}
```

## Render Deployment

1. Push repo to GitHub
2. New Web Service → connect repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add env var: `ANTHROPIC_API_KEY` in Render dashboard
