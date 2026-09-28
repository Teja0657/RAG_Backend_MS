import os
import time
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from api_gateway.database import SessionLocal
from admin_service.database import SessionLocal as AdminSessionLocal
from admin_service.models import EvaluationMetric
from admin_service.internal_auth import (
    verify_internal_secret,
    INTERNAL_SERVICE_SECRET,
)
from evaluation.runner import run_evaluation

router = APIRouter(dependencies=[Depends(verify_internal_secret)])

RAG_SERVICE_URL = os.getenv(
    "RAG_SERVICE_URL",
    "http://127.0.0.1:8001",
)
DOCUMENT_SERVICE_URL = os.getenv(
    "DOCUMENT_SERVICE_URL",
    "http://127.0.0.1:8002",
)
INTERNAL_AUTH_HEADERS = {"X-Internal-Secret": INTERNAL_SERVICE_SECRET}


class TestChatRequest(BaseModel):
    question: str

@router.get("/internal/overview")
async def get_overview(request: Request):
    # --------------------------------------------------
    # MySQL statistics
    # --------------------------------------------------
    db: Session = SessionLocal()
    try:
        registered_users = db.execute(
            text("""
                SELECT COUNT(DISTINCT user_id)
                FROM conversations
            """)
        ).scalar() or 0
        total_queries = db.execute(
            text("""
                SELECT COUNT(*)
                FROM messages
                WHERE role = 'user'
            """)
        ).scalar() or 0
        recent_activity_rows = db.execute(
            text("""
                SELECT
                    c.user_id,
                    m.content,
                    m.created_at
                FROM messages m
                JOIN conversations c
                    ON c.id = m.conversation_id
                WHERE m.role = 'user'
                ORDER BY m.created_at DESC
                LIMIT 10
            """)
        ).fetchall()
    finally:
        db.close()
    # -------------------------------------------------
    # RAG statistics
    # --------------------------------------------------
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{RAG_SERVICE_URL}/internal/stats",
            headers=INTERNAL_AUTH_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        rag_stats = response.json()
    # --------------------------------------------------
    # Recent activity
    # --------------------------------------------------
    recent_activity = [
        {
            "user_id": row.user_id,
            "text": row.content,
            "created_at": row.created_at,
        }
        for row in recent_activity_rows
    ]
    return {
        "indexed_chunks": rag_stats["indexed_chunks"],
        "registered_users": registered_users,
        "total_queries": total_queries,
        "recent_activity": recent_activity,
    } 

@router.get("/internal/users")
def get_users():
    db: Session = SessionLocal()

    try:
        rows = db.execute(text("""
            SELECT
                u.auth0_user_id,
                u.email,
                COUNT(m.id) AS query_count
            FROM users u
            LEFT JOIN conversations c
                ON c.user_id = u.auth0_user_id
            LEFT JOIN messages m
                ON m.conversation_id = c.id
                AND m.role = 'user'
            WHERE u.role != 'admin'
            GROUP BY
                u.id,
                u.auth0_user_id,
                u.email
            ORDER BY query_count DESC
        """)).fetchall()

        return {
            "users": [
                {
                    "user_id": row.auth0_user_id,
                    "email": row.email,
                    "query_count": row.query_count,
                }
                for row in rows
            ]
        }

    finally:
        db.close()


# ==========================================================
# EVALUATION — run the LangSmith dataset, cache the summary
# ==========================================================

@router.post("/internal/evaluation/run")
def run_evaluation_endpoint():
    summary = run_evaluation()
    evaluated_at = datetime.utcnow()

    admin_db = AdminSessionLocal()

    try:
        for metric_name, metric in summary["metrics"].items():
            admin_db.add(EvaluationMetric(
                run_id=summary["run_id"],
                run_url=summary.get("url"),
                metric_name=metric_name,
                score=metric["score"],
                total_examples=metric["total_examples"],
                passed_examples=metric["passed_examples"],
                failed_examples=metric["failed_examples"],
                evaluated_at=evaluated_at,
            ))

        admin_db.commit()
    finally:
        admin_db.close()

    return {
        "status": "completed",
        "run_id": summary["run_id"],
        "run_url": summary.get("url"),
        "total_examples": summary["total_examples"],
        "evaluated_at": evaluated_at,
        "metrics": summary["metrics"],
    }


# ==========================================================
# STATS — reporting only, never touches the RAG pipeline
# ==========================================================

@router.get("/internal/stats")
async def get_stats():
    db: Session = SessionLocal()

    try:
        total_queries = db.execute(
            text("SELECT COUNT(*) FROM messages WHERE role = 'user'")
        ).scalar() or 0
    finally:
        db.close()

    async with httpx.AsyncClient() as client:
        rag_response = await client.get(
            f"{RAG_SERVICE_URL}/internal/stats",
            headers=INTERNAL_AUTH_HEADERS,
            timeout=10,
        )
        rag_response.raise_for_status()
        rag_stats = rag_response.json()

        document_response = await client.get(
            f"{DOCUMENT_SERVICE_URL}/internal/documents/stats",
            headers=INTERNAL_AUTH_HEADERS,
            timeout=10,
        )
        document_response.raise_for_status()
        document_stats = document_response.json()

    admin_db = AdminSessionLocal()

    try:
        latest = (
            admin_db.query(EvaluationMetric)
            .order_by(EvaluationMetric.evaluated_at.desc())
            .first()
        )

        evaluation = None

        if latest is not None:
            rows = (
                admin_db.query(EvaluationMetric)
                .filter(EvaluationMetric.run_id == latest.run_id)
                .all()
            )

            evaluation = {
                "run_id": latest.run_id,
                "run_url": latest.run_url,
                "evaluated_at": latest.evaluated_at,
                "total_examples": max(
                    (row.total_examples for row in rows),
                    default=0,
                ),
                "metrics": {
                    row.metric_name: row.score
                    for row in rows
                },
            }
    finally:
        admin_db.close()

    return {
        "documents": document_stats,
        "rag": {
            "indexed_chunks": rag_stats["indexed_chunks"],
        },
        "queries": {
            "total": total_queries,
        },
        "evaluation": evaluation,
    }


# ==========================================================
# TEST CHAT — a single live probe against the RAG pipeline
# ==========================================================

@router.post("/internal/test-chat")
async def test_chat(request: TestChatRequest):
    start_time = time.perf_counter()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{RAG_SERVICE_URL}/internal/query",
            json={"question": request.question},
            headers=INTERNAL_AUTH_HEADERS,
            timeout=None,
        )
        response.raise_for_status()
        rag_result = response.json()

    elapsed_ms = round((time.perf_counter() - start_time) * 1000)

    return {
        "answer": rag_result["answer"],
        "conversation_id": None,
        "elapsed_ms": elapsed_ms,
        "timings": rag_result.get("timings"),
        "trace_url": rag_result.get("trace_url"),
    }