from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from mpost_api.db import get_db
from mpost_api.routes.search import SearchRequest, SearchResult, search_documents

router = APIRouter()


class PersonaRecommendationRequest(BaseModel):
    echelon: str = Field(min_length=1)
    job_title: str = Field(min_length=1)
    mp_unit_type: str = Field(min_length=1)
    mission_context: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


@router.post("/recommendations", response_model=list[SearchResult])
def recommend_for_persona(
    request: PersonaRecommendationRequest,
    db: Annotated[Session, Depends(get_db)],
) -> list[SearchResult]:
    query_parts = [
        request.echelon,
        request.job_title,
        request.mp_unit_type,
    ]
    if request.mission_context:
        query_parts.append(request.mission_context)

    return search_documents(
        SearchRequest(
            query=" ".join(query_parts),
            limit=request.limit,
            echelon=None,
            mp_unit_type=None,
        ),
        db,
    )
