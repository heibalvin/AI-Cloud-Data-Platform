from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import (
    init_db,
    create_thread,
    list_threads,
    get_thread,
    add_message,
    get_messages,
    delete_thread,
    get_latest_assistant_message,
)
from message import publish_chat_request


router = APIRouter(prefix="/api")


class ThreadCreate(BaseModel):
    title: Optional[str] = None


class ThreadOut(BaseModel):
    id: str
    title: str
    updated_at: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class ChatRequest(BaseModel):
    thread_id: Optional[str] = None
    message: str
    model: str = "llama3.1:8b"


class ChatResponse(BaseModel):
    thread_id: str
    status: str


@app.on_event("startup")
async def startup():
    await init_db()
    # Ensure a default thread exists so there is always one available
    existing = await list_threads()
    if not existing:
        await create_thread("Welcome")
        print("[api] created default thread 'Welcome'")


@router.get("/threads", response_model=List[ThreadOut])
async def api_list_threads():
    return await list_threads()


@app.post("/api/threads", response_model=ThreadOut)
async def api_create_thread(thread: ThreadCreate):
    return await create_thread(thread.title)


@app.get("/api/threads/{thread_id}", response_model=dict)
async def api_get_thread(thread_id: str):
    thread = await get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    messages = await get_messages(thread_id)
    return {"thread": thread, "messages": messages}


@app.delete("/api/threads/{thread_id}")
async def api_delete_thread(thread_id: str):
    ok = await delete_thread(thread_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"status": "deleted"}


@app.post("/api/chat", response_model=ChatResponse)
async def api_chat(req: ChatRequest):
    """Nginx/frontend pushes a chat request to Kafka topic chat.requests."""
    thread_id = req.thread_id
    if not thread_id:
        thread = await create_thread(None)
        thread_id = thread["id"]

    await publish_chat_request(thread_id, req.message, req.model)
    print(f"[api] produced request to Kafka thread={thread_id}")
    return ChatResponse(thread_id=thread_id, status="queued")


@app.get("/api/threads/{thread_id}/response", response_model=dict)
async def api_latest_response(thread_id: str):
    """Frontend polls for the latest Ollama answer."""
    msg = await get_latest_assistant_message(thread_id)
    if not msg:
        return {"thread_id": thread_id, "response": None, "status": "pending"}
    return {
        "thread_id": thread_id,
        "response": msg["content"],
        "created_at": msg["created_at"],
        "status": "done",
    }