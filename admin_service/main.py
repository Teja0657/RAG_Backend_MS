from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from admin_service.database import Base, engine
from admin_service.models import EvaluationMetric
from admin_service.routes.admin import router as admin_router

Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Admin Service",
    version="1.0.0"
)


@app.get("/internal/health")
def health_check():

    return {
        "status": "ok",
        "service": "admin-service"
    }

app.include_router(admin_router)