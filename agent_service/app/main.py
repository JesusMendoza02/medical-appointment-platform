from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from app.database import engine
from app.models import Base
from app.schemas import ChatRequest, ChatResponse
from app.agent import run_agent_chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Crea las tablas en la BD al arrancar la aplicación."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Citas Médicas — AI Agent API",
    description="API para la gestión de citas médicas con agente de IA (Ollama)",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["Health"])
async def health_check():
    """Verifica que el servidor esté en línea."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse, tags=["Agent"])
async def chat_with_agent(payload: ChatRequest):
    """Envía un mensaje al agente de IA y recibe una respuesta en lenguaje natural."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    try:
        agent_reply = await run_agent_chat(payload.message)
        return ChatResponse(response=agent_reply)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en el procesamiento del agente: {str(e)}"
        )
