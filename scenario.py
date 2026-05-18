import os

_active = "default"


def get() -> str:
    return _active


def switch(name: str) -> None:
    global _active
    _active = name


def resolve(base_path: str) -> str:
    """Return scenario-specific path if it exists, otherwise fall back to base."""
    if _active == "default":
        return base_path
    stem, ext = os.path.splitext(base_path)
    candidate = f"{stem}_{_active}{ext}"
    return candidate if os.path.isfile(candidate) else base_path
