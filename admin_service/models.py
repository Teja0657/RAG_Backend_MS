from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
)

from admin_service.database import Base


class EvaluationMetric(Base):

    __tablename__ = "evaluation_metrics"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    run_id = Column(
        String(255),
        nullable=False,
        index=True,
    )

    run_url = Column(
        String(500),
        nullable=True,
    )

    metric_name = Column(
        String(100),
        nullable=False,
    )

    score = Column(
        Float,
        nullable=False,
    )

    total_examples = Column(
        Integer,
        nullable=False,
    )

    passed_examples = Column(
        Integer,
        nullable=False,
    )

    failed_examples = Column(
        Integer,
        nullable=False,
    )

    evaluated_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
