"""Helpers for building prompts and generating AI responses."""

from . import config
from .clients import openai_client
from .memory import chat_history


def build_messages(user_id: str):
    """Build the message list (system prompt + history) sent to the model."""

    history = chat_history[user_id]

    return [
        {
            "role": "system",
            "content": config.SYSTEM_PROMPT,
        },
        *history,
    ]


async def generate_response(user_id: str, text: str):
    """
    Generate AI response.
    """

    history = chat_history[user_id]

    # User message
    history.append(
        {
            "role": "user",
            "content": text,
        }
    )

    try:
        response = await openai_client.chat.completions.create(
            model=config.MODEL,
            messages=build_messages(user_id),
            max_tokens=config.MAX_OUTPUT_TOKENS,
            temperature=0.6,
        )

        reply = response.choices[0].message.content

        if not reply:
            raise RuntimeError("Empty response from AI")

        # Assistant message
        history.append(
            {
                "role": "assistant",
                "content": reply,
            }
        )

        return reply

    except Exception:
        # Roll back the user message if the API call failed.
        if history and history[-1]["role"] == "user":
            history.pop()

        raise
