import asyncio
import json
from typing import Optional, Dict, Any

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

from database import (
    create_thread,
    add_message,
    get_latest_assistant_message,
)
from llm import get_llm_response
from environment import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_REQUEST_TOPIC,
    KAFKA_RESPONSE_TOPIC,
)

producer: Optional[AIOKafkaProducer] = None


async def start_producer():
    global producer
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()
    print(f"[message] Kafka producer started, bootstrap={KAFKA_BOOTSTRAP_SERVERS}")


async def stop_producer():
    global producer
    if producer:
        await producer.stop()
        producer = None


async def publish_chat_request(thread_id: str, message: str, model: str) -> None:
    """Publish a chat request to Kafka chat.requests topic."""
    if not producer:
        raise RuntimeError("Kafka producer not initialized")
    await producer.send_and_wait(
        KAFKA_REQUEST_TOPIC,
        {"thread_id": thread_id, "message": message, "model": model},
    )
    print(f"[message] produced request to Kafka thread={thread_id}")


async def publish_chat_response(thread_id: str, response: str) -> None:
    """Publish a chat response to Kafka chat.responses topic."""
    if not producer:
        raise RuntimeError("Kafka producer not initialized")
    await producer.send_and_wait(
        KAFKA_RESPONSE_TOPIC,
        {"thread_id": thread_id, "response": response},
    )
    print(f"[message] produced response to Kafka thread={thread_id}")


async def consume_requests_with_retry():
    """Background task: consume chat.requests, call LLM, publish responses."""
    while True:
        try:
            await _consume_requests()
        except Exception as ex:
            print(f"[message] Kafka consumer error: {ex}; retrying in 5s")
            await asyncio.sleep(5)


async def _consume_requests():
    """Kafka consumer: listens to chat.requests, calls LLM, publishes chat.responses."""
    consumer = AIOKafkaConsumer(
        KAFKA_REQUEST_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="aicd_chat",
    )
    await consumer.start()
    print(f"[message] Kafka consumer started, topic={KAFKA_REQUEST_TOPIC}")
    try:
        async for msg in consumer:
            payload = msg.value
            thread_id = payload.get("thread_id")
            user_message = payload.get("message", "")
            model = payload.get("model", "llama3.1:8b")

            print(f"[message] consumed request thread={thread_id} msg={user_message[:40]}...")

            if not thread_id:
                from database import create_thread
                thread = await create_thread(None)
                thread_id = thread["id"]
                print(f"[message] created thread={thread_id}")

            from database import add_message
            await add_message(thread_id, "user", user_message)

            from llm import get_llm_response
            assistant_text = await get_llm_response(thread_id, user_message, model)

            await add_message(thread_id, "assistant", assistant_text)

            await publish_chat_response(thread_id, assistant_text)
            print(f"[message] produced response thread={thread_id}")
    finally:
        await consumer.stop()