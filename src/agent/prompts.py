SYSTEM_PROMPT = """\
You are Vela, a helpful assistant.
You may use tools when it helps answer the user.
Keep responses concise and accurate.
"""


def format_user_message(text: str) -> dict:
    return {"role": "user", "content": text}


def format_assistant_message(text: str) -> dict:
    return {"role": "assistant", "content": text}

