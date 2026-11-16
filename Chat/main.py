import asyncio
import json
import os
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

from db import (
    init_db,
    create_thread,
    list_threads,
    get_thread,
    add_message,
    get_messages,
    delete_thread,
    get_latest_assistant_message,
)
from llm import get_llm_response

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "aicd_kafka:9092")
KAFKA_REQUEST_TOPIC = os.getenv("KAFKA_REQUEST_TOPIC", "chat.requests")
KAFKA_RESPONSE_TOPIC = os.getenv("KAFKA_RESPONSE_TOPIC", "chat.responses")

app = FastAPI(title="AICD Ollama Chat (Kafka-driven)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

producer: Optional[AIOKafkaProducer] = None


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
    global producer
    await init_db()
    # Ensure a default thread exists so there is always one available
    existing = await list_threads()
    if not existing:
        await create_thread("Welcome")
        print("[chat] created default thread 'Welcome'")
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()
    print(f"[chat] Kafka producer started, bootstrap={KAFKA_BOOTSTRAP_SERVERS}")
    asyncio.create_task(consume_requests_with_retry())


@app.on_event("shutdown")
async def shutdown():
    global producer
    if producer:
        await producer.stop()


async def consume_requests_with_retry():
    while True:
        try:
            await _consume_requests()
        except Exception as ex:
            print(f"[chat] Kafka consumer error: {ex}; retrying in 5s")
            await asyncio.sleep(5)


async def _consume_requests():
    """Kafka consumer: listens to chat.requests, calls Ollama, publishes chat.responses."""
    consumer = AIOKafkaConsumer(
        KAFKA_REQUEST_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="aicd_chat",
    )
    await consumer.start()
    print(f"[chat] Kafka consumer started, topic={KAFKA_REQUEST_TOPIC}")
    try:
        async for msg in consumer:
            payload = msg.value
            thread_id = payload.get("thread_id")
            user_message = payload.get("message", "")
            model = payload.get("model", "llama3.1:8b")

            print(f"[chat] consumed request thread={thread_id} msg={user_message[:40]}...")

            if not thread_id:
                thread = await create_thread(None)
                thread_id = thread["id"]
                print(f"[chat] created thread={thread_id}")

            await add_message(thread_id, "user", user_message)

            assistant_text = await get_llm_response(thread_id, user_message, model)

            await add_message(thread_id, "assistant", assistant_text)

            await producer.send_and_wait(
                KAFKA_RESPONSE_TOPIC,
                {"thread_id": thread_id, "response": assistant_text},
            )
            print(f"[chat] produced response thread={thread_id}")
    finally:
        await consumer.stop()


@app.get("/api/threads", response_model=List[ThreadOut])
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

    await producer.send_and_wait(
        KAFKA_REQUEST_TOPIC,
        {"thread_id": thread_id, "message": req.message, "model": req.model},
    )
    print(f"[chat] produced request to Kafka thread={thread_id}")
    return ChatResponse(thread_id=thread_id, status="queued")


@app.get("/api/threads/{thread_id}/response", response_model=dict)
async def api_latest_response(thread_id: str):
    """Frontend polls for the latest Ollama answer (from chat.responses via Postgres)."""
    msg = await get_latest_assistant_message(thread_id)
    if not msg:
        return {"thread_id": thread_id, "response": None, "status": "pending"}
    return {
        "thread_id": thread_id,
        "response": msg["content"],
        "created_at": msg["created_at"],
        "status": "done",
    }
