import json
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from ai_client import (
    AIClientError,
    generate_chat_reply,
    improve_prompt_with_editor,
)
from dataset_builder import Sample, build_samples, load_conversations
from prompt_store import get_latest_prompt, save_new_prompt


load_dotenv()

app = Flask(__name__)


@app.get("/health")
def health() -> Any:
    return jsonify({"status": "ok"})


def _normalize_chat_history(raw_history: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    for msg in raw_history:
        role = msg.get("role")
        text = msg.get("message", "")
        if role not in ("client", "consultant"):
            continue
        normalized.append({"role": role, "message": text})
    print('kuay')
    return normalized


@app.post("/generate-reply")
def generate_reply_endpoint() -> Any:
    """
    Generate an AI response based on conversation context.
    """
    data = request.get_json(force=True, silent=True) or {}
    client_sequence = data.get("clientSequence")
    chat_history = data.get("chatHistory", [])

    if not isinstance(client_sequence, str) or not client_sequence.strip():
        return (
            jsonify({"error": "clientSequence must be a non-empty string"}),
            400,
        )

    if not isinstance(chat_history, list):
        return jsonify({"error": "chatHistory must be a list"}), 400

    payload = {
        "clientSequence": client_sequence,
        "chatHistory": _normalize_chat_history(chat_history),
    }

    try:
        reply = generate_chat_reply(payload)
    except AIClientError as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify({"aiReply": reply})


@app.post("/improve-ai")
def improve_ai_endpoint() -> Any:
    """
    Auto-improve the AI prompt by comparing predicted vs actual consultant reply.
    """
    data = request.get_json(force=True, silent=True) or {}

    client_sequence = data.get("clientSequence")
    chat_history = data.get("chatHistory", [])
    consultant_reply = data.get("consultantReply")

    if not isinstance(client_sequence, str) or not client_sequence.strip():
        return (
            jsonify({"error": "clientSequence must be a non-empty string"}),
            400,
        )
    if not isinstance(consultant_reply, str) or not consultant_reply.strip():
        return (
            jsonify({"error": "consultantReply must be a non-empty string"}),
            400,
        )
    if not isinstance(chat_history, list):
        return jsonify({"error": "chatHistory must be a list"}), 400

    normalized_history = _normalize_chat_history(chat_history)

    try:
        predicted_reply = generate_chat_reply(
            {"clientSequence": client_sequence, "chatHistory": normalized_history}
        )
    except AIClientError as exc:
        return jsonify({"error": str(exc)}), 500

    existing_prompt = get_latest_prompt()

    try:
        updated_prompt = improve_prompt_with_editor(
            existing_prompt=existing_prompt,
            client_sequence=client_sequence,
            chat_history=normalized_history,
            consultant_reply=consultant_reply,
            predicted_reply=predicted_reply,
        )
    except AIClientError as exc:
        return jsonify({"error": str(exc)}), 500

    save_new_prompt(updated_prompt)

    return jsonify(
        {
            "predictedReply": predicted_reply,
            "updatedPrompt": updated_prompt,
        }
    )


@app.post("/improve-ai-manually")
def improve_ai_manually_endpoint() -> Any:
    """
    Manually update the AI prompt with specific instructions (no LLM call needed).
    """
    data = request.get_json(force=True, silent=True) or {}
    instructions = data.get("instructions")

    if not isinstance(instructions, str) or not instructions.strip():
        return (
            jsonify({"error": "instructions must be a non-empty string"}),
            400,
        )

    current_prompt = get_latest_prompt()
    manual_update = (
        current_prompt.strip()
        + "\n\n# Additional manual instructions\n"
        + instructions.strip()
    )
    updated_prompt = save_new_prompt(manual_update)

    return jsonify({"updatedPrompt": updated_prompt})


def run_self_learning_pipeline(
    limit: int | None = 20,
) -> None:
    """
    Offline helper: iterate over samples from conversations.json and refine the prompt.

    This is not exposed as an HTTP endpoint; you can run it manually:
        python app.py self_learn
    """
    from prompt_store import get_latest_prompt, save_new_prompt

    root = Path(__file__).resolve().parent
    conversations_path = root / "conversations.json"
    conversations = load_conversations(conversations_path)
    samples: List[Sample] = build_samples(conversations)

    if limit is not None:
        samples = samples[:limit]

    prompt = get_latest_prompt()
    for idx, s in enumerate(samples, start=1):
        client_seq_text = "\n".join(s.client_sequence)
        consultant_reply_text = "\n".join(s.consultant_reply)
        history_for_model: List[Dict[str, str]] = []
        for m in s.chat_history:
            role = "client" if m.get("direction") == "in" else "consultant"
            history_for_model.append({"role": role, "message": m.get("text", "")})

        try:
            predicted = generate_chat_reply(
                {
                    "clientSequence": client_seq_text,
                    "chatHistory": history_for_model,
                }
            )
            prompt = improve_prompt_with_editor(
                existing_prompt=prompt,
                client_sequence=client_seq_text,
                chat_history=history_for_model,
                consultant_reply=consultant_reply_text,
                predicted_reply=predicted,
            )
            save_new_prompt(prompt)
            print(f"[{idx}] Updated prompt using sample from {s.contact_id}")
        except AIClientError as exc:
            print(f"[{idx}] Skipped sample due to AI error: {exc}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "self_learn":
        run_self_learning_pipeline()
    else:
        app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))

