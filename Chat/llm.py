import os
from typing import List, Dict, Any

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from db import get_messages

SYSTEM_PROMPT = (
    "You are a helpful AI assistant. "
    "Answer the user's questions clearly and concisely."
)


async def get_llm_response(thread_id: str, user_message: str, model: str) -> str:
    llm = ChatOllama(model=model, base_url=os.getenv("OLLAMA_BASE_URL", "http://aicd_ollama:11434"))

    messages: List[Any] = [SystemMessage(content=SYSTEM_PROMPT)]

    history = await get_messages(thread_id)
    for m in history:
        if m["role"] == "user":
            messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            messages.append(AIMessage(content=m["content"]))

    messages.append(HumanMessage(content=user_message))

    result = await llm.ainvoke(messages)
    return result.content
