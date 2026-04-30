#!/usr/bin/env python3
"""Search past conversations, excluding the last 6 messages sent by the user."""

import json
import sys
from pathlib import Path


def load_conversations(filepath: str) -> list[dict]:
    with open(filepath) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return data.get("conversations", [])


def get_user_messages(messages: list[dict]) -> list[dict]:
    return [m for m in messages if m.get("role") == "user"]


def filter_last_n_user_messages(messages: list[dict], n: int = 6) -> list[dict]:
    """Return messages with the last n user messages excluded."""
    user_msgs = get_user_messages(messages)
    if len(user_msgs) <= n:
        excluded = set(id(m) for m in user_msgs)
    else:
        excluded = set(id(m) for m in user_msgs[-n:])
    return [m for m in messages if id(m) not in excluded]


def search_conversations(conversations: list[dict], query: str) -> list[dict]:
    """Search conversations for query, ignoring the last 6 user messages in each."""
    results = []
    query_lower = query.lower()

    for convo in conversations:
        messages = convo.get("messages", [])
        searchable = filter_last_n_user_messages(messages, n=6)

        matches = []
        for msg in searchable:
            content = msg.get("content", "")
            if isinstance(content, list):
                text = " ".join(
                    part.get("text", "") for part in content if isinstance(part, dict)
                )
            else:
                text = str(content)

            if query_lower in text.lower():
                matches.append({
                    "role": msg.get("role"),
                    "snippet": text[:200].strip(),
                })

        if matches:
            results.append({
                "conversation_id": convo.get("id", "unknown"),
                "title": convo.get("title", "Untitled"),
                "match_count": len(matches),
                "matches": matches,
            })

    return results


def print_results(results: list[dict]) -> None:
    if not results:
        print("No matches found.")
        return

    print(f"Found {len(results)} conversation(s) with matches:\n")
    for r in results:
        print(f"[{r['conversation_id']}] {r['title']}  ({r['match_count']} match(es))")
        for m in r["matches"]:
            print(f"  [{m['role']}] {m['snippet']}")
        print()


def main():
    if len(sys.argv) < 3:
        print("Usage: python search_conversations.py <conversations.json> <query>")
        sys.exit(1)

    filepath = sys.argv[1]
    query = " ".join(sys.argv[2:])

    if not Path(filepath).exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    conversations = load_conversations(filepath)
    results = search_conversations(conversations, query)
    print_results(results)


if __name__ == "__main__":
    main()
