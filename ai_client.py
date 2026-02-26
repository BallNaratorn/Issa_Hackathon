import json
import os
from typing import Any, Dict

from openai import OpenAI, OpenAIError

from prompt_store import get_latest_prompt


class AIClientError(Exception):
    pass


def _get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise AIClientError(
            "OPENAI_API_KEY is not set. Please configure it in your .env file."
        )
    return OpenAI(api_key=api_key)


def _get_model_name() -> str:
    # Default to a capable but cost-effective model; user can override.
    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def generate_chat_reply(payload: Dict[str, Any]) -> str:
    """
    Generate an AI reply in natural, consultant-style language.

    Returns the reply text (not the full JSON).
    """
    base_prompt = get_latest_prompt()
    system_prompt = base_prompt

    client = _get_openai_client()

    try:
        completion = client.chat.completions.create(
            model=_get_model_name(),
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ],
            temperature=0.4,
        )
    except OpenAIError as exc:
        raise AIClientError(f"Error calling OpenAI: {exc}") from exc

    message_content = completion.choices[0].message.content or "{}"
    try:
        parsed = json.loads(message_content)
    except json.JSONDecodeError as exc:
        raise AIClientError(
            f"Model did not return valid JSON. Raw content: {message_content}"
        ) from exc

    reply = parsed.get("reply")
    if not isinstance(reply, str):
        raise AIClientError(
            f"Model JSON missing 'reply' field or not a string: {parsed}"
        )
    return reply


EDITOR_PROMPT = """
You are an expert AI prompt engineer helping improve a visa-consultant chatbot prompt.

You will be given:
1) existingPrompt: the current chatbot system prompt
2) clientSequence: latest 1+ client messages
3) chatHistory: previous messages in the conversation
4) consultantReply: the real reply written by a human Issa Compass consultant
5) predictedReply: the reply produced by the AI using existingPrompt

Your job:
- Carefully compare consultantReply vs predictedReply
- Infer what is missing or wrong in existingPrompt (logic, style, tone, sales motions, risk warnings, etc.)
- Make **surgical** edits to existingPrompt to better match the human consultant behaviour
- Preserve all good parts of the prompt; only change what is necessary

You MUST respond in JSON format only:
{ "prompt": "the full updated system prompt, as a string" }
""".strip()


def improve_prompt_with_editor(
    existing_prompt: str,
    client_sequence: str,
    chat_history: list[dict],
    consultant_reply: str,
    predicted_reply: str,
) -> str:
    """
    Use the editor prompt to generate an improved version of the system prompt.
    """
    client = _get_openai_client()
    payload = {
        "existingPrompt": existing_prompt,
        "clientSequence": client_sequence,
        "chatHistory": chat_history,
        "consultantReply": consultant_reply,
        "predictedReply": predicted_reply,
    }

    try:
        completion = client.chat.completions.create(
            model=_get_model_name(),
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": EDITOR_PROMPT,
                },
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ],
            temperature=0.3,
        )
    except OpenAIError as exc:
        raise AIClientError(f"Error calling OpenAI editor: {exc}") from exc

    message_content = completion.choices[0].message.content or "{}"
    try:
        parsed = json.loads(message_content)
    except json.JSONDecodeError as exc:
        raise AIClientError(
            f"Editor model did not return valid JSON. Raw content: {message_content}"
        ) from exc

    new_prompt = parsed.get("prompt")
    if not isinstance(new_prompt, str):
        raise AIClientError(
            f"Editor JSON missing 'prompt' field or not a string: {parsed}"
        )
    return new_prompt

