from fastapi import FastAPI
from admin_service.routes.admin import router as admin_router


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