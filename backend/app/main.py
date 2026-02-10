from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.openai_client import OpenAIServiceError
from app.rag import ask_question, semantic_search
from app.schemas import AskRequest, AskResponse, SearchResult

app = FastAPI(title="AI Research Radar API")

origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/search", response_model=list[SearchResult])
def search(
    q: str = Query(..., min_length=1),
    k: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[SearchResult]:
    try:
        return semantic_search(db=db, query=q, k=k)
    except OpenAIServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
    if payload.k < 1 or payload.k > 50:
        raise HTTPException(status_code=422, detail="k must be between 1 and 50")

    try:
        return ask_question(db=db, query=payload.query, k=payload.k)
    except OpenAIServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
