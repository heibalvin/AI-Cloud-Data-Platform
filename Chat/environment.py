import os
from typing import Optional

# Postgres
POSTGRES_URI = os.getenv(
    "POSTGRES_URI",
    "postgresql://aicd:aicd@aicd_postgres:5432/aicd",
)

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://aicd_ollama:11434")

# Kafka
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "aicd_kafka:9092")
KAFKA_REQUEST_TOPIC = os.getenv("KAFKA_REQUEST_TOPIC", "chat.requests")
KAFKA_RESPONSE_TOPIC = os.getenv("KAFKA_RESPONSE_TOPIC", "chat.responses")

# Service
SERVICE_NAME = os.getenv("SERVICE_NAME", "aicd_chat")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.1.0")