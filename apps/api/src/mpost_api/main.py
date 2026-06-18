from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mpost_api.config import settings
from mpost_api.routes import admin, auth, chat, documents, health, personas, search

app = FastAPI(title="MPOST API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(personas.router, prefix="/personas", tags=["personas"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
