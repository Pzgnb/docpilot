from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.base import SessionDependency
from app.db.models import KnowledgeBase
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseRead


router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge-bases"])


def not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "KNOWLEDGE_BASE_NOT_FOUND", "message": "知识库不存在"},
    )


@router.post("", response_model=KnowledgeBaseRead, status_code=status.HTTP_201_CREATED)
def create_knowledge_base(
    payload: KnowledgeBaseCreate, session: SessionDependency
) -> KnowledgeBase:
    knowledge_base = KnowledgeBase(
        name=payload.name,
        description=payload.description,
    )
    session.add(knowledge_base)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "KNOWLEDGE_BASE_EXISTS", "message": "知识库名称已存在"},
        ) from exc
    session.refresh(knowledge_base)
    return knowledge_base


@router.get("", response_model=list[KnowledgeBaseRead])
def list_knowledge_bases(session: SessionDependency) -> list[KnowledgeBase]:
    statement = select(KnowledgeBase).order_by(KnowledgeBase.created_at)
    return list(session.scalars(statement))


@router.get("/{knowledge_base_id}", response_model=KnowledgeBaseRead)
def get_knowledge_base(
    knowledge_base_id: UUID, session: SessionDependency
) -> KnowledgeBase:
    knowledge_base = session.get(KnowledgeBase, str(knowledge_base_id))
    if knowledge_base is None:
        raise not_found()
    return knowledge_base


@router.delete("/{knowledge_base_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge_base(
    knowledge_base_id: UUID, session: SessionDependency
) -> Response:
    knowledge_base = session.get(KnowledgeBase, str(knowledge_base_id))
    if knowledge_base is None:
        raise not_found()
    session.delete(knowledge_base)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
