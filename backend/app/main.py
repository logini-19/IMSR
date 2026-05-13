from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


from app.api.v1 import forecasts, fl as fl_router, leave, doctors

app.include_router(forecasts.router, prefix="/api/v1")
app.include_router(fl_router.router, prefix="/api/v1")
app.include_router(leave.router, prefix="/api/v1")
app.include_router(doctors.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}
