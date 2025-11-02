def sanitize_username(name: str) -> str:
    return "".join(ch for ch in name.strip() if ch.isalnum() or ch in ("_", "-"))[:24]
