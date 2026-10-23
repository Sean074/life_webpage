"""Web front-end logic for the ATMOS engine (github.com/Sean074/20_ATMOS).

Public, anonymous page — every input is validated against a whitelist or a
finite numeric range before it reaches the engine, and engine errors come back
as messages rather than exceptions.
"""
import io
import json
import math
import threading
from functools import lru_cache

import atmos
from atmos import plot_speed_alt
from atmos import unit_convert as u_c
from matplotlib.figure import Figure

_MODEL_LABELS = {
    "standard_atmos_1976.csv": "US Standard Atmosphere 1976",
    "standard_atmos.csv": "Nelson, Flight Stability and Automatic Control",
}
MODELS = {name: _MODEL_LABELS.get(name, name) for name in atmos.list_models()}
DEFAULT_MODEL = "standard_atmos_1976.csv" if "standard_atmos_1976.csv" in MODELS else next(iter(MODELS))


def _envelope_label(path: str) -> str:
    with open(path) as f:
        return json.load(f).get("name", path)


ENVELOPES = {"": "None — grid only"}
ENVELOPES.update({name: _envelope_label(path) for name, path in atmos.list_envelopes().items()})

CHART_TYPES = {"kcas": "KCAS", "keas": "KEAS", "ktas": "KTAS"}

SPEED_TYPES = {"mach": "Mach", "ktas": "KTAS", "kcas": "KCAS", "keas": "KEAS"}
_SPEED_CALC = {"mach": atmos.mach_alt, "ktas": atmos.tas_alt, "kcas": atmos.cas_alt, "keas": atmos.eas_alt}

ALT_UNITS = {"ft": 1.0, "m": u_c.M_FT}
SPEED_UNITS = {"kts": 1.0, "m/s": u_c.MS_KTS}
PRESSURE_UNITS = {"psf": 1.0, "psi": u_c.PSI_PSF, "pa": u_c.PA_PSF, "atm": u_c.ATM_PSF, "bar": u_c.BAR_PSF}

# Generous outer bounds; the atmospheric model enforces the real altitude/pressure range.
_ALT_FT_LIMIT = 1_000_000
_PRESSURE_PSF_LIMIT = 100_000
_MACH_MAX = 5.0
_SPEED_KTS_MAX = 3000


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


def _model_path(model: str) -> str:
    return atmos.list_models()[model]


def atmos_props(model: str, mode: str, raw_value: str | None, unit: str) -> dict:
    """Atmospheric properties at a pressure altitude or a static pressure.

    Returns {"errors": {field: msg}} or {"result": {...}} or {"message": str}.
    """
    errors = {}
    if model not in MODELS:
        errors["model"] = "unknown model"
    if mode == "altitude":
        if unit not in ALT_UNITS:
            errors["unit"] = "unknown unit"
        value, err = parse_float(raw_value, -_ALT_FT_LIMIT, _ALT_FT_LIMIT)
    elif mode == "pressure":
        if unit not in PRESSURE_UNITS:
            errors["unit"] = "unknown unit"
        value, err = parse_float(raw_value, 0, _PRESSURE_PSF_LIMIT)
    else:
        errors["mode"] = "unknown input type"
        value, err = None, None
    if err:
        errors["value"] = err
    if errors:
        return {"errors": errors}

    try:
        with atmos.use_model(_model_path(model)):
            if mode == "altitude":
                result = atmos.get_atmos_prop_alt(value * ALT_UNITS[unit])
            else:
                result = atmos.get_atmos_prop_pres(value * PRESSURE_UNITS[unit])
    except atmos.AtmosRangeError as e:
        return {"message": str(e)}
    return {"result": {k: float(v) for k, v in result.items()}}


def speed_convert(model: str, raw_alt: str | None, alt_unit: str, speed_type: str,
                  raw_value: str | None, unit: str) -> dict:
    """Convert one airspeed at a pressure altitude to Mach, KTAS, KEAS, KCAS and q_c.

    Returns {"errors": {field: msg}} or {"result": {...}} or {"message": str}.
    """
    errors = {}
    if model not in MODELS:
        errors["model"] = "unknown model"
    if alt_unit not in ALT_UNITS:
        errors["alt_unit"] = "unknown unit"
    alt, err = parse_float(raw_alt, -_ALT_FT_LIMIT, _ALT_FT_LIMIT)
    if err:
        errors["alt"] = err
    if speed_type not in SPEED_TYPES:
        errors["speed_type"] = "unknown speed type"
        value = None
    elif speed_type == "mach":
        value, err = parse_float(raw_value, 0, _MACH_MAX)
        if err:
            errors["value"] = err
    else:
        if unit not in SPEED_UNITS:
            errors["unit"] = "unknown unit"
        value, err = parse_float(raw_value, 0, _SPEED_KTS_MAX)
        if err:
            errors["value"] = err
    if errors:
        return {"errors": errors}

    speed = value if speed_type == "mach" else value * SPEED_UNITS[unit]
    alt_ft = alt * ALT_UNITS[alt_unit]
    try:
        with atmos.use_model(_model_path(model)):
            result = _SPEED_CALC[speed_type](speed, alt_ft)
    except atmos.AtmosRangeError as e:
        return {"message": str(e)}
    except (RuntimeError, ValueError, ZeroDivisionError, OverflowError):
        return {"message": "The solver could not converge for that input."}
    return {"result": {"alt_ft": alt_ft, **{k: float(v) for k, v in result.items()}}}


_chart_lock = threading.Lock()


def chart_params_valid(model: str, x_type: str, envelope: str) -> bool:
    return model in MODELS and x_type in CHART_TYPES and envelope in ENVELOPES


@lru_cache(maxsize=len(MODELS) * len(CHART_TYPES) * len(ENVELOPES))
def chart_svg(model: str, x_type: str, envelope: str) -> str:
    """Speed-altitude chart as SVG text. Call chart_params_valid() first.

    Every parameter comes from a small whitelist, so the cache holds every
    possible chart and each is rendered at most once per process. The lock keeps
    at most one render (~1 s of CPU) running at a time.
    """
    envelope_path = atmos.list_envelopes()[envelope] if envelope else None
    with _chart_lock, atmos.use_model(_model_path(model)):
        fig = Figure(figsize=plot_speed_alt.FIGSIZE_IN)
        plot_speed_alt.draw_speed_alt(fig, x_type, envelope_path)
        buf = io.StringIO()
        fig.savefig(buf, format="svg")
    return buf.getvalue()
