"""
Rinox Sentinel - Utility Helpers
"""

import re
from typing import Optional


def sanitize(text: str, max_length: int = 2000) -> str:
    """Remove Discord markdown and trim text"""
    cleaned = re.sub(r'[*_~`|>]', '', text)
    return cleaned[:max_length]


def truncate(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration"""
    parts = []
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)


def parse_duration(text: str) -> Optional[int]:
    """Parse duration string (e.g., '1h30m', '2d', '45m') into seconds"""
    total = 0
    patterns = [
        (r'(\d+)\s*d', 86400),
        (r'(\d+)\s*h', 3600),
        (r'(\d+)\s*m', 60),
        (r'(\d+)\s*s', 1),
    ]
    for pattern, multiplier in patterns:
        match = re.search(pattern, text.lower())
        if match:
            total += int(match.group(1)) * multiplier
    return total if total > 0 else None