"""Load the project catalog ONCE and render a compact knowledge block.

Design goals (latency-first):
  * Zero runtime retrieval. The file is parsed a single time at process start
    (``@lru_cache``) and the rendered text is reused for every call.
  * Small token footprint via a TWO-TIER model: statutory / builder-level facts
    (GST, stamp duty, legal, credibility, loan banks, plot rules) are stated
    ONCE as shared blocks; only per-project facts (price, location, possession…)
    repeat. The LLM answers every question category directly, with no tool call.

The file may be YAML (default) or JSON; the format is picked by extension.
Override the location with the ``PROJECT_DATA_PATH`` env var.

Supports two shapes:
  * catalog  : shared builder info + a ``projects:`` list (current).
  * single   : a flat single project (legacy) — wrapped into a 1-item catalog.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from priya.config import settings
from priya.utils.logging import get_logger

log = get_logger(__name__)

_DEFAULT_PATH = Path(__file__).parent / "project.yaml"


@dataclass(slots=True)
class Project:
    """Per-project facts (only what varies between projects)."""

    id: str = ""
    project_name: str = ""
    property_type: str = ""
    location: str = ""
    price: str = ""
    total_cost: str = ""
    possession: str = ""
    carpet_area: str = ""
    parking: str = ""
    maintenance: str = ""
    construction_status: str = ""
    rera: str = ""
    connectivity: str = ""
    road_width: str = ""
    amenities: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass(slots=True)
class ProjectData:
    """Shared builder info (Tier 1) + the project catalog (Tier 2)."""

    builder_name: str = ""
    builder_description: str = ""
    region: str = ""
    # Credibility
    years_in_business: str = ""
    completed_projects: str = ""
    track_record: str = ""
    penalty_clause: str = ""
    # Contact
    site_visit_contact: str = ""
    whatsapp_number: str = ""
    brochure_available: bool = False
    # Finance
    loan_banks: list[str] = field(default_factory=list)
    emi_estimate: str = ""
    # Shared dict blocks
    cost_breakup: dict = field(default_factory=dict)
    legal: dict = field(default_factory=dict)
    plot_info: dict = field(default_factory=dict)
    market_note: str = ""
    # Catalog
    projects: list[Project] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectData":
        raw_projects = data.get("projects")
        if raw_projects:
            projects = [Project.from_dict(p) for p in raw_projects]
        elif data.get("project_name"):
            # Legacy single-project file: wrap the flat top level as one project.
            projects = [Project.from_dict(data)]
        else:
            projects = []
        return cls(
            builder_name=data.get("builder_name", ""),
            builder_description=data.get("builder_description", ""),
            region=data.get("region", ""),
            years_in_business=data.get("years_in_business", ""),
            completed_projects=data.get("completed_projects", ""),
            track_record=data.get("track_record", ""),
            penalty_clause=data.get("penalty_clause", ""),
            site_visit_contact=data.get("site_visit_contact", ""),
            whatsapp_number=data.get("whatsapp_number", ""),
            brochure_available=bool(data.get("brochure_available", False)),
            loan_banks=data.get("loan_banks", []) or [],
            emi_estimate=data.get("emi_estimate", ""),
            cost_breakup=data.get("cost_breakup", {}) or {},
            legal=data.get("legal", {}) or {},
            plot_info=data.get("plot_info", {}) or {},
            market_note=data.get("market_note", ""),
            projects=projects,
        )

    def has_plots(self) -> bool:
        return any(p.property_type.lower() == "plot" for p in self.projects)


def _load_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    return yaml.safe_load(text) or {}


@lru_cache(maxsize=1)
def get_project() -> ProjectData:
    """Return the parsed catalog (loaded once, cached for the process)."""
    path = Path(settings.project_data_path) if settings.project_data_path else _DEFAULT_PATH
    if not path.exists():
        log.error("project.data.missing", path=str(path))
        return ProjectData()
    data = _load_file(path)
    project = ProjectData.from_dict(data)
    log.info(
        "project.data.loaded",
        path=str(path),
        builder=project.builder_name,
        projects=len(project.projects),
    )
    return project


def _render_project_line(index: int, p: Project) -> str:
    head_meta = ", ".join(x for x in (p.property_type, p.location) if x)
    head = f"{index}. {p.project_name}"
    if head_meta:
        head = f"{head} — {head_meta}"

    detail: list[str] = []
    if p.price:
        detail.append(f"Price: {p.price}")
    if p.possession:
        detail.append(f"Possession: {p.possession}")
    if p.carpet_area:
        detail.append(f"Carpet: {p.carpet_area}")
    if p.rera:
        detail.append(f"RERA: {p.rera}")
    if p.maintenance:
        detail.append(f"Maintenance: {p.maintenance}")
    if p.parking:
        detail.append(f"Parking: {p.parking}")
    if p.construction_status:
        detail.append(f"Status: {p.construction_status}")
    if p.road_width:
        detail.append(f"Road: {p.road_width}")
    if p.amenities:
        detail.append(f"Amenities: {', '.join(p.amenities)}")
    if p.connectivity:
        detail.append(f"Connectivity: {p.connectivity}")

    body = " ".join(f"{d}." for d in detail)
    return f"{head}. {body}".strip()


def _render_shared(p: ProjectData) -> list[str]:
    """Tier-1 blocks stated once: credibility, finance, charges, legal, plots."""
    lines: list[str] = []

    # Builder / credibility
    if p.builder_name:
        desc = f" — {p.builder_description}" if p.builder_description else ""
        lines.append(f"Builder: {p.builder_name}{desc}")
    cred = []
    if p.years_in_business:
        cred.append(f"{p.years_in_business} experience")
    if p.completed_projects:
        cred.append(p.completed_projects)
    if p.track_record:
        cred.append(p.track_record)
    if cred:
        lines.append("Track record: " + "; ".join(cred) + ".")
    if p.penalty_clause:
        lines.append(f"Delay/penalty: {p.penalty_clause}.")

    # Finance
    fin = []
    if p.loan_banks:
        fin.append(f"Loan approved by {', '.join(p.loan_banks)}")
    if p.emi_estimate:
        fin.append(f"EMI example: {p.emi_estimate}")
    if fin:
        lines.append("Home loan: " + ". ".join(fin) + ".")

    # Cost break-up
    cb = p.cost_breakup
    if cb:
        parts = [cb.get("gst"), cb.get("stamp_duty_registration"), cb.get("hidden_charges")]
        parts = [x for x in parts if x]
        if parts:
            lines.append("Charges & taxes: " + " ".join(f"{x}." for x in parts))

    # Legal
    lg = p.legal
    if lg:
        parts = [lg.get("title"), lg.get("approvals"), lg.get("oc_cc")]
        parts = [x for x in parts if x]
        if parts:
            lines.append("Legal: " + " ".join(f"{x}." for x in parts))

    # Plot rules (only if catalog has plots)
    pi = p.plot_info
    if pi and p.has_plots():
        parts = [pi.get("registry"), pi.get("mutation"), pi.get("land_use"), pi.get("govt_approval")]
        parts = [x for x in parts if x]
        if parts:
            lines.append("Plots (registry/legal): " + " ".join(f"{x}." for x in parts))

    # Market / investment
    if p.market_note:
        lines.append(f"Investment/appreciation: {p.market_note}.")

    # Contact
    contact = p.site_visit_contact or p.whatsapp_number
    if contact:
        lines.append(f"Site visit / WhatsApp: {contact}.")
    if p.brochure_available:
        lines.append("Brochure: available to send on WhatsApp.")

    return lines


@lru_cache(maxsize=1)
def render_project_knowledge() -> str:
    """Render Tier-1 shared blocks + the Tier-2 catalog as a compact fact block.

    Cached so the string is built exactly once and shared across all calls.
    """
    p = get_project()
    lines: list[str] = _render_shared(p)
    if p.region:
        lines.insert(1 if p.builder_name else 0, f"Region: {p.region}")

    lines.append("")
    lines.append("Projects (answer ONLY from this list; never invent a project, price or detail):")
    for i, proj in enumerate(p.projects, 1):
        lines.append(_render_project_line(i, proj))

    return "\n".join(lines)
