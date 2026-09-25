import os

import httpx
from fastapi import APIRouter, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from api_gateway.database import SessionLocal

router = APIRouter()

RAG_SERVICE_URL = os.getenv(
    "RAG_SERVICE_URL",
    "http://127.0.0.1:8001",
)

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