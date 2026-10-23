"""Form-value parsing shared by the public /projects/<tool> pages."""
import math


def parse_float(raw: str | None, lo: float, hi: float) -> tuple[float | None, str | None]:
    """Parse a form value into a finite float in (lo, hi]. Returns (value, error)."""
    if raw is None or not raw.strip():
        return None, "required"
    try:
        value = float(raw)
    except ValueError:
        return None, "not a number"
    if not math.isfinite(value):
        return None, "not a number"
    if not lo < value <= hi:
        return None, f"must be greater than {lo:g} and at most {hi:g}"
    return value, None


def parse_int(raw: str | None, lo: int, hi: int) -> tuple[int | None, str | None]:
    """Parse a form value into an int in [lo, hi]. Returns (value, error)."""
    if raw is None or not raw.strip():
        return None, "required"
    try:
        value = int(raw)
    except ValueError:
        return None, "not a whole number"
    if not lo <= value <= hi:
        return None, f"must be from {lo} to {hi}"
    return value, None
