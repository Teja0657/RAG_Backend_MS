from sqlalchemy.orm import Session

from api_gateway.models import Conversation, Message


def create_conversation(
    db: Session,
    user_id: str,
    title: str,
) -> Conversation:

    conversation = Conversation(
        user_id=user_id,
        title=title,
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


def get_user_conversations(
    db: Session,
    user_id: str,
) -> list[Conversation]:

    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
        .all()
    )


def get_conversation(
    db: Session,
    conversation_id: int,
    user_id: str,
) -> Conversation | None:

    return (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        .first()
    )


def add_message(
    db: Session,
    conversation_id: int,
    role: str,
    content: str,
) -> Message:

    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message

def get_conversation_messages(
    db: Session,
    converstion_id: int,
    user_id :str,    
) -> Conversation|None:
    return (
        db.query(Conversation)
        .filter(
            Conversation.id == converstion_id,
            Conversation.user_id == user_id
        )
        .first()
    )

def rename_conversation(
    db: Session,
    conversation_id: int,
    user_id: str,
    title: str,
) -> Conversation | None:
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        .first()
    )

    if conversation is None:
        return None

    conversation.title = title

    db.commit()
    db.refresh(conversation)

    return conversation


def update_pin_status(
    db: Session,
    conversation_id: int,
    user_id: str,
    pinned: bool,
) -> Conversation | None:
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        .first()
    )

    if conversation is None:
        return None

    if pinned:
        pinned_count = (
            db.query(Conversation)
            .filter(
                Conversation.user_id == user_id,
                Conversation.pinned == True,
            )
            .count()
        )

        if pinned_count >= 3:
            return "limit_reached"

    conversation.pinned = pinned

    db.commit()
    db.refresh(conversation)

    return conversation

def delete_conversation(
    db: Session,
    conversation_id: int,
    user_id: str,
) -> bool:
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        .first()
    )

    if conversation is None:
        return False

    db.delete(conversation)
    db.commit()

    return True