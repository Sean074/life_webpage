"""Web front-end logic for the 2D flutter engine (github.com/Sean074/30_2DFlutter).

Public, anonymous page. Unlike ATMOS the inputs are open-ended, so every field is
bounded, the sweep is capped at MAX_POINTS, the solver settings stay at the
engine defaults (bounded iterations), and only one solve runs at a time.
Results for identical inputs are cached, which covers the presets.
"""
import io
import threading
from functools import lru_cache

import numpy as np
from flutter2d.analysis.flutter import (
    build_mass_matrix,
    build_stiffness_matrix,
    compute_flutter,
    compute_structural_frequencies,
    find_flutter_speed,
)
from flutter2d.plotting.plots import FIGSIZE_IN, draw_vg_vf
from matplotlib.figure import Figure

from app.services.tool_inputs import parse_float, parse_int

MAX_POINTS = 500
_LOCK_WAIT_S = 10

# Form field -> (label, unit, lo, hi); values must lie in (lo, hi].
SECTION_FIELDS = {
    "b_m": ("Semi-chord b", "m", 0, 10),
    "a_h_nd": ("Elastic axis a", "b", -1, 1),
    "x_alpha_nd": ("CG offset xα", "b", -1, 1),
    "mass_kg": ("Mass m", "kg", 0, 10_000),
    "inertia_alpha_kg_m2": ("Pitch inertia Iα", "kg m²", 0, 10_000),
    "omega_heave_rad_s": ("Heave frequency ωh", "rad/s", 0, 1_000),
    "omega_alpha_rad_s": ("Pitch frequency ωα", "rad/s", 0, 1_000),
    "rho_kg_m3": ("Air density ρ", "kg/m³", 0, 10),
}
FLAP_FIELDS = {
    "c_hinge_nd": ("Hinge c", "b", -1, 1),
    "x_beta_nd": ("Flap CG offset xβ", "b", -1, 1),
    "inertia_beta_kg_m2": ("Flap inertia Iβ", "kg m²", 0, 1_000),
    "omega_beta_rad_s": ("Flap frequency ωβ", "rad/s", 0, 1_000),
}
SWEEP_FIELDS = {
    "v_min_m_s": ("Speed from", "m/s", 0, 1_000),
    "v_max_m_s": ("Speed to", "m/s", 0, 1_000),
}
DOF_CHOICES = {"2": "2 — heave, pitch", "3": "3 — heave, pitch, flap"}

_SHIPPED = {
    "b_m": 0.5, "a_h_nd": -0.2, "x_alpha_nd": 0.1, "mass_kg": 10.0,
    "inertia_alpha_kg_m2": 0.5, "omega_heave_rad_s": 10.0, "omega_alpha_rad_s": 25.0,
    "rho_kg_m3": 1.225,
    "c_hinge_nd": 0.6, "x_beta_nd": 0.0125, "inertia_beta_kg_m2": 0.0156, "omega_beta_rad_s": 30.0,
}
# Each preset is a complete set of form values (strings, as a query string would carry).
PRESETS = {
    "shipped": ("Shipped defaults", {**_SHIPPED, "dof": "2", "v_min_m_s": 1, "v_max_m_s": 100, "n_points": 200}),
    "flap": ("Flap example", {**_SHIPPED, "dof": "3", "v_min_m_s": 1, "v_max_m_s": 60, "n_points": 200}),
    "stable": ("Stable section (CG ahead of EA)", {
        **_SHIPPED, "b_m": 0.5, "a_h_nd": 0.25, "x_alpha_nd": -0.5, "mass_kg": 10.4,
        "inertia_alpha_kg_m2": 1.12, "omega_heave_rad_s": 20.0, "omega_alpha_rad_s": 21.0,
        "rho_kg_m3": 1.21, "dof": "2", "v_min_m_s": 1, "v_max_m_s": 50, "n_points": 200,
    }),
}
PRESETS = {key: (label, {k: str(v) for k, v in values.items()}) for key, (label, values) in PRESETS.items()}
DEFAULT_VALUES = PRESETS["shipped"][1]


def parse_form(raw: dict) -> dict:
    """Validate form values. Returns {"errors": {field: msg}} or {"inputs": {...}}."""
    errors, inputs = {}, {}
    dof = raw.get("dof", "")
    if dof not in DOF_CHOICES:
        errors["dof"] = "choose 2 or 3"
    fields = {**SECTION_FIELDS, **SWEEP_FIELDS, **(FLAP_FIELDS if dof == "3" else {})}
    for name, (_label, _unit, lo, hi) in fields.items():
        inputs[name], err = parse_float(raw.get(name), lo, hi)
        if err:
            errors[name] = err
        elif name in ("a_h_nd", "c_hinge_nd") and inputs[name] == 1:
            errors[name] = "must be less than 1 (the trailing edge)"
    inputs["n_points"], err = parse_int(raw.get("n_points"), 2, MAX_POINTS)
    if err:
        errors["n_points"] = err
    if not ({"v_min_m_s", "v_max_m_s"} & errors.keys()) and inputs["v_max_m_s"] <= inputs["v_min_m_s"]:
        errors["v_max_m_s"] = "must be greater than the starting speed"
    if errors:
        return {"errors": errors}
    inputs["flap"] = dof == "3"
    return {"inputs": inputs}


_solve_lock = threading.Lock()


def run(inputs: dict) -> dict:
    """Solve a validated section. Returns {"result": {...}} or {"message": str}."""
    key = tuple(sorted(inputs.items()))
    if not _solve_lock.acquire(timeout=_LOCK_WAIT_S):
        return {"message": "The solver is busy. Try again in a moment."}
    try:
        return _solve(key)
    finally:
        _solve_lock.release()


@lru_cache(maxsize=32)
def _solve(key: tuple) -> dict:
    """p-k sweep, flutter points and the V-g / V-f chart as inline SVG text."""
    d = dict(key)
    b_m, flap = d["b_m"], d["flap"]
    k_heave_n_m = d["omega_heave_rad_s"] ** 2 * d["mass_kg"]
    k_alpha_nm_rad = d["omega_alpha_rad_s"] ** 2 * d["inertia_alpha_kg_m2"]
    velocity_range_m_s = np.linspace(d["v_min_m_s"], d["v_max_m_s"], d["n_points"])
    try:
        with np.errstate(all="ignore"):
            if flap:
                mass_matrix_kg = build_mass_matrix(
                    d["mass_kg"], d["inertia_alpha_kg_m2"], b_m, d["x_alpha_nd"],
                    d["x_beta_nd"], d["inertia_beta_kg_m2"], d["c_hinge_nd"], d["a_h_nd"],
                )
                k_beta_nm_rad = d["omega_beta_rad_s"] ** 2 * d["inertia_beta_kg_m2"]
            else:
                mass_matrix_kg = build_mass_matrix(d["mass_kg"], d["inertia_alpha_kg_m2"], b_m, d["x_alpha_nd"])
                k_beta_nm_rad = None
            stiffness_matrix_n_m = build_stiffness_matrix(k_heave_n_m, k_alpha_nm_rad, k_beta_nm_rad)
            omega_arr_rad_s = compute_structural_frequencies(mass_matrix_kg, stiffness_matrix_n_m)
            p_arr_modes = compute_flutter(
                mass_matrix_kg, stiffness_matrix_n_m, velocity_range_m_s, d["rho_kg_m3"], b_m,
                d["a_h_nd"], c_hinge_nd=d["c_hinge_nd"] if flap else None,
            )
    except (ValueError, ArithmeticError) as e:
        return {"message": str(e)}

    modes, p_modes = [], {}
    for idx, (omega_rad_s, p_arr) in enumerate(zip(omega_arr_rad_s, p_arr_modes), start=1):
        p_modes[f"MODE {idx} ({omega_rad_s:.2f} rad/s)"] = p_arr
        point = find_flutter_speed(p_arr, velocity_range_m_s, b_m)
        lost = np.flatnonzero(np.isnan(p_arr))
        modes.append({
            "number": idx,
            "omega_rad_s": float(omega_rad_s),
            "v_flutter_m_s": point[0] if point else None,
            "omega_flutter_rad_s": point[1] if point else None,
            # p-k cannot follow a mode past here (frequency to zero or no convergence).
            "ends_at_m_s": float(velocity_range_m_s[lost[0]]) if len(lost) else None,
        })

    fig = Figure(figsize=FIGSIZE_IN)
    with np.errstate(all="ignore"):
        draw_vg_vf(fig, velocity_range_m_s, p_modes, b_m, title="Flutter V-g / V-f (p-k method)")
    buf = io.StringIO()
    fig.savefig(buf, format="svg")
    svg = buf.getvalue()
    svg = svg[svg.index("<svg"):]  # drop the XML prolog and DOCTYPE for inline use
    return {"result": {"modes": modes, "svg": svg}}
