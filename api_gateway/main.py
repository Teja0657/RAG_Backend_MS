from fastapi import FastAPI, Depends
from api_gateway.auth import get_current_user, require_admin

from api_gateway.routes.chat import router as chat_router
from api_gateway.routes.documents import router as documents_router
from api_gateway.routes.admin import router as admin_router


from fastapi.middleware.cors import CORSMiddleware
from api_gateway.database import engine
from api_gateway.models import Base

app=FastAPI(
    title="RAG API Gateway",
    version="1.0.0"
)
Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/internal/health")
def health_checks():
    return{
        "status":"ok",
        "service": "api-gateway"
    }

@app.get("/api/me")
def get_me(current_user=Depends(get_current_user)):
    return{
        "user_id": current_user["sub"],
        "claims": current_user,
    }



app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(admin_router)