FROM python:3.12-slim

ARG VERSION=1.0.0

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OLLAMA_BASE_URL=http://aicd_ollama:11434 \
    POSTGRES_URI=postgresql://aicd:aicd@aicd_postgres:5432/aicd \
    KAFKA_BOOTSTRAP_SERVERS=aicd_kafka:9092 \
    KAFKA_REQUEST_TOPIC=chat.requests \
    KAFKA_RESPONSE_TOPIC=chat.responses \
    AICD_VERSION=${VERSION}

LABEL org.opencontainers.image.version=${VERSION} \
      org.opencontainers.image.title="aicd-chat" \
      org.opencontainers.image.description="AICD Ollama chat backend with Kafka, LangChain and Postgres"

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
