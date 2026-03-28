from __future__ import annotations

import random
import time

from openai import APIError, OpenAI, RateLimitError

from app.services.config import settings


class OpenAIServiceError(RuntimeError):
    pass


def build_openai_client() -> OpenAI:
    if not settings.openai_api_key:
        raise OpenAIServiceError("OPENAI_API_KEY is required")
    return OpenAI(api_key=settings.openai_api_key)

def _with_retry(fn, retries: int = 5, base_sleep: float = 2.0, max_sleep: float = 30.0):
    for attempt in range(retries):
        try:
            return fn()
        except RateLimitError as exc:
            if attempt == retries - 1:
                raise
            sleep_for = min(max_sleep, base_sleep * (2**attempt)) + random.uniform(0, 1.0)
            time.sleep(sleep_for)
        except APIError as exc:
            status = getattr(exc, "status_code", None)
            if status is not None and status >= 500 and attempt < retries - 1:
                sleep_for = min(max_sleep, base_sleep * (2**attempt)) + random.uniform(0, 1.0)
                time.sleep(sleep_for)
                continue
            raise


def embed_texts(texts: list[str]) -> list[list[float]]:
    client = build_openai_client()
    try:
        response = _with_retry(lambda: client.embeddings.create(model=settings.openai_embedding_model, input=texts))
        return [item.embedding for item in response.data]
    except RateLimitError as exc:
        raise OpenAIServiceError(
            "OpenAI quota/rate limit exceeded. Check billing/quota and API key."
        ) from exc
    except APIError as exc:
        raise OpenAIServiceError(f"OpenAI embeddings request failed: {exc}") from exc


def chat_with_context(query: str, context_blocks: list[str]) -> str:
    client = build_openai_client()
    context = "\n\n".join(context_blocks)
    prompt = (
        "Answer the user question using only the provided context. "
        "If context is insufficient, say that clearly. Keep it concise.\n\n"
        f"Question: {query}\n\nContext:\n{context}"
    )
    try:
        completion = _with_retry(
            lambda: client.chat.completions.create(
                model=settings.openai_chat_model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": "You are a precise research assistant."},
                    {"role": "user", "content": prompt},
                ],
            )
        )
    except RateLimitError as exc:
        raise OpenAIServiceError(
            "OpenAI quota/rate limit exceeded. Check billing/quota and API key."
        ) from exc
    except APIError as exc:
        raise OpenAIServiceError(f"OpenAI chat request failed: {exc}") from exc
    return completion.choices[0].message.content or "No answer generated."


def chat_markdown(system_prompt: str, user_prompt: str) -> str:
    client = build_openai_client()
    try:
        completion = _with_retry(
            lambda: client.chat.completions.create(
                model=settings.openai_chat_model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        )
    except RateLimitError as exc:
        raise OpenAIServiceError(
            "OpenAI quota/rate limit exceeded. Check billing/quota and API key."
        ) from exc
    except APIError as exc:
        raise OpenAIServiceError(f"OpenAI chat request failed: {exc}") from exc
    return completion.choices[0].message.content or "No markdown generated."
