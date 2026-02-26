import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


ConversationMessage = dict


@dataclass
class Sample:
    contact_id: str
    scenario: str
    client_sequence: List[str]
    consultant_reply: List[str]
    chat_history: List[ConversationMessage]


def load_conversations(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_samples(conversations: list[dict]) -> list[Sample]:
    samples: list[Sample] = []

    for convo in conversations:
        contact_id = convo.get("contact_id", "")
        scenario = convo.get("scenario", "")
        messages: list[ConversationMessage] = convo.get("conversation", [])

        history: list[ConversationMessage] = []
        i = 0
        n = len(messages)

        while i < n:
            msg = messages[i]
            direction = msg.get("direction")

            if direction == "in":
                client_seq: list[ConversationMessage] = []
                while i < n and messages[i].get("direction") == "in":
                    client_seq.append(messages[i])
                    i += 1

                consultant_seq: list[ConversationMessage] = []
                while i < n and messages[i].get("direction") == "out":
                    consultant_seq.append(messages[i])
                    i += 1

                client_texts = [m.get("text", "") for m in client_seq]
                consultant_texts = [m.get("text", "") for m in consultant_seq]

                samples.append(
                    Sample(
                        contact_id=contact_id,
                        scenario=scenario,
                        client_sequence=client_texts,
                        consultant_reply=consultant_texts,
                        chat_history=list(history),
                    )
                )

                history.extend(client_seq)
                history.extend(consultant_seq)
            else:
                history.append(msg)
                i += 1

    return samples


def print_sample_preview(samples: Iterable[Sample], limit: int = 3) -> None:
    for idx, s in enumerate(samples):
        if idx >= limit:
            break
        print("=" * 80)
        print(f"Sample #{idx + 1}")
        print(f"Contact: {s.contact_id} | Scenario: {s.scenario}")
        print("\nChat history:")
        for h in s.chat_history:
            role = "CLIENT" if h.get("direction") == "in" else "CONSULTANT"
            print(f"- ({role}) {h.get('text')}")
        print("\nClient sequence:")
        for t in s.client_sequence:
            print(f"- {t}")
        print("\nConsultant reply:")
        for t in s.consultant_reply:
            print(f"- {t}")
        print()


def main() -> None:
    root = Path(__file__).resolve().parent
    conversations_path = root / "conversations.json"
    if not conversations_path.exists():
        raise SystemExit(f"conversations.json not found at {conversations_path}")

    conversations = load_conversations(conversations_path)
    samples = build_samples(conversations)

    print(f"Built {len(samples)} samples from conversations.json")
    print_sample_preview(samples, limit=3)


if __name__ == "__main__":
    main()

