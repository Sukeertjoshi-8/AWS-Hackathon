from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# ── Route imports ──────────────────────────────────────────────────────────────
from routes.text_route import router as text_router

from routes.image_route import router as image_router
from routes.deepfake_route import router as deepfake_router

# ── App init ───────────────────────────────────────────────────────────────────
app = FastAPI(
    title="FakeScope Backend",
    description="Scam detection API for Indian users powered by Claude AI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to frontend domain before production
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles

# ── Register routers ───────────────────────────────────────────────────────────
app.include_router(text_router)
app.include_router(image_router)
app.include_router(deepfake_router)


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["Infra"])
def health():
    """Health check — used by Render to confirm the service is up."""
    return {"status": "ok", "service": "fakescope-backend"}


# ── Serve Frontend UI ─────────────────────────────────────────────────────────
app.mount("/", StaticFiles(directory="static", html=True), name="static")

