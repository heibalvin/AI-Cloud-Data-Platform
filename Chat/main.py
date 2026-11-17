import asyncio
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, create_thread, list_threads
from message import start_producer, stop_producer, consume_requests_with_retry
from api import router as api_router

app = FastAPI(title="AICD Ollama Chat (Kafka-driven)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the API routes
app.include_router(api_router)


@app.on_event("startup")
async def startup():
    await init_db()
    # Ensure a default thread exists so there is always one available
    existing = await list_threads()
    if not existing:
        from database import create_thread
        await create_thread("Welcome")
        print("[main] created default thread 'Welcome'")
    await start_producer()
    asyncio.create_task(consume_requests_with_retry())
    print("[main] Chat service started")


@app.on_event("shutdown")
async def shutdown():
    await stop_producer()
    print("[main] Chat service stopped")