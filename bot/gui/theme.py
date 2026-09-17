"""Color palette + font constants shared by every view in the GUI."""

COLORS = {
    "bg": "#0f172a",
    "header_bg": "#111827",
    "chat_bg": "#0b1220",
    "sidebar_bg": "#111827",
    "input_bg": "#1e293b",
    "field_bg": "#0b1220",
    "muted": "#9ca3af",
    "text": "#e5e7eb",
    "user_bubble": "#1f2937",
    "bot_bubble": "#2563eb",
    "bot_cache_bubble": "#0d9488",
    "bot_system_bubble": "#4b5563",
    "bot_error_bubble": "#b91c1c",
    "accent": "#2563eb",
    "accent_hover": "#1d4ed8",
    "danger": "#ef4444",
    "danger_hover": "#991b1b",
    "ok": "#22c55e",
    "warn": "#f59e0b",
}


META_FONT = ("Segoe UI", 9)
MSG_FONT = ("Segoe UI", 10)
HEADER_FONT = ("Segoe UI", 13, "bold")
LABEL_FONT = ("Segoe UI", 10, "bold")


PLATFORM_NAME_EN = {
    "telegram": "Telegram",
    "rubika": "Rubika",
}


def platform_name_en(platform: str) -> str:
    """Display name for a platform id, or empty if unknown."""

    return PLATFORM_NAME_EN.get(platform, "")
