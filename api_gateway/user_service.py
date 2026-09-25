from datetime import datetime

from sqlalchemy import select

from api_gateway.database import SessionLocal
from api_gateway.models import User


def upsert_user(user_data: dict):
    auth0_user_id = user_data.get("sub")

    if not auth0_user_id:
        raise ValueError("Missing Auth0 user ID")

    email = user_data.get("https://myapp.example.com/email")
    name = user_data.get("https://myapp.example.com/name")

    roles = user_data.get(
        "https://myapp.example.com/roles",
        []
    )

    role = "admin" if "admin" in roles else "user"

    db = SessionLocal()

    try:
        user = db.scalar(
            select(User).where(
                User.auth0_user_id == auth0_user_id
            )
        )

        if user is None:
            user = User(
                auth0_user_id=auth0_user_id,
                email=email or "",
                name=name,
                role=role,
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow(),
            )

            db.add(user)

        else:
            user.email = email or user.email
            user.name = name
            user.role = role
            user.last_login = datetime.utcnow()

        db.commit()
        db.refresh(user)

        return user

    finally:
        db.close()