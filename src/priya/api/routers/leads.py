"""Leads API — production-ready, fully tenant-scoped.

Endpoints:
  GET    /leads              list + search + filters + pagination
  POST   /leads              create a lead (manual)
  GET    /leads/export       CSV export of the filtered set
  POST   /leads/import       bulk CSV import (multipart upload)
  GET    /leads/{id}         lead detail incl. calls + appointments
  PATCH  /leads/{id}         update
  DELETE /leads/{id}         delete (admin+)

Filters: status, source, qualification-score range, created-at date range,
free-text search (name/phone/city/location).
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from priya.api.schemas import (
    AppointmentItem,
    CallSummaryItem,
    LeadCreate,
    LeadDetailResponse,
    LeadImportError,
    LeadImportResult,
    LeadListResponse,
    LeadResponse,
    LeadUpdate,
)
from priya.auth.dependencies import CurrentUser, get_current_user, get_db, require_role
from priya.db.models import LeadSource, LeadStatus, PropertyType, UserRole
from priya.db.repositories import (
    AppointmentRepository,
    CallRepository,
    LeadRepository,
)
from priya.utils.logging import get_logger

router = APIRouter(prefix="/leads", tags=["leads"])
log = get_logger(__name__)

_SORT_FIELDS = {"created_at", "updated_at", "qualification_score", "name"}


def _filters(
    status_: LeadStatus | None,
    source: LeadSource | None,
    score_min: int | None,
    score_max: int | None,
    date_from: datetime | None,
    date_to: datetime | None,
    search: str | None,
) -> dict:
    return {
        "status": status_,
        "source": source,
        "score_min": score_min,
        "score_max": score_max,
        "date_from": date_from,
        "date_to": date_to,
        "search": search,
    }


# --------------------------------------------------------------------------- #
# List
# --------------------------------------------------------------------------- #
@router.get("", response_model=LeadListResponse)
async def list_leads(
    status_: LeadStatus | None = Query(default=None, alias="status"),
    source: LeadSource | None = Query(default=None),
    score_min: int | None = Query(default=None, ge=0, le=100),
    score_max: int | None = Query(default=None, ge=0, le=100),
    date_from: datetime | None = Query(default=None, description="created_at >= (ISO 8601)"),
    date_to: datetime | None = Query(default=None, description="created_at <= (ISO 8601)"),
    search: str | None = Query(default=None, max_length=120),
    sort_by: str = Query(default="created_at"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> LeadListResponse:
    if sort_by not in _SORT_FIELDS:
        raise HTTPException(status_code=422, detail=f"sort_by must be one of {sorted(_SORT_FIELDS)}")
    filters = _filters(status_, source, score_min, score_max, date_from, date_to, search)
    repo = LeadRepository(session)
    rows = await repo.list_filtered(
        user.tenant_id,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        descending=(order == "desc"),
        **filters,
    )
    total = await repo.count_filtered(user.tenant_id, **filters)
    return LeadListResponse(
        items=[LeadResponse.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


# --------------------------------------------------------------------------- #
# Create
# --------------------------------------------------------------------------- #
@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreate,
    user: CurrentUser = Depends(require_role(UserRole.agent)),
    session: AsyncSession = Depends(get_db),
) -> LeadResponse:
    repo = LeadRepository(session)
    if await repo.get_by_phone(payload.phone_number, tenant_id=user.tenant_id):
        raise HTTPException(status_code=409, detail="Lead with this phone already exists")
    row = await repo.create(user.tenant_id, **payload.model_dump())
    log.info("leads.create", tenant=str(user.tenant_id), phone=row.phone_number)
    return LeadResponse.model_validate(row)


# --------------------------------------------------------------------------- #
# CSV export (declared before /{lead_id} so "export" isn't parsed as an id)
# --------------------------------------------------------------------------- #
_EXPORT_COLUMNS = [
    "id", "name", "phone_number", "city", "property_type", "budget_min", "budget_max",
    "preferred_location", "buying_timeline", "purpose", "loan_required",
    "site_visit_interest", "preferred_language", "status", "source",
    "qualification_score", "created_at", "updated_at",
]


@router.get("/export")
async def export_leads(
    status_: LeadStatus | None = Query(default=None, alias="status"),
    source: LeadSource | None = Query(default=None),
    score_min: int | None = Query(default=None, ge=0, le=100),
    score_max: int | None = Query(default=None, ge=0, le=100),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    search: str | None = Query(default=None, max_length=120),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    filters = _filters(status_, source, score_min, score_max, date_from, date_to, search)
    rows = await LeadRepository(session).stream_filtered(user.tenant_id, **filters)

    def _iter():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(_EXPORT_COLUMNS)
        yield buf.getvalue()
        for lead in rows:
            buf.seek(0)
            buf.truncate(0)
            writer.writerow([_cell(lead, c) for c in _EXPORT_COLUMNS])
            yield buf.getvalue()

    filename = f"leads_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    log.info("leads.export", tenant=str(user.tenant_id), count=len(rows))
    return StreamingResponse(
        _iter(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _cell(lead, column: str):  # noqa: ANN001
    val = getattr(lead, column, None)
    if val is None:
        return ""
    if hasattr(val, "value"):  # enum
        return val.value
    if isinstance(val, datetime):
        return val.isoformat()
    return val


# --------------------------------------------------------------------------- #
# CSV import
# --------------------------------------------------------------------------- #
_IMPORT_TEXT_FIELDS = {
    "name", "city", "preferred_location", "buying_timeline", "purpose", "preferred_language"
}
_IMPORT_FLOAT_FIELDS = {"budget_min", "budget_max"}
_IMPORT_BOOL_FIELDS = {"loan_required", "site_visit_interest"}
_TRUE = {"true", "1", "yes", "y", "haan"}
_FALSE = {"false", "0", "no", "n", "nahi"}


def _parse_bool(raw: str) -> bool | None:
    v = raw.strip().lower()
    if v in _TRUE:
        return True
    if v in _FALSE:
        return False
    return None


def _parse_row(row: dict[str, str]) -> dict:
    """Map a CSV row (case-insensitive headers) to Lead fields."""
    norm = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
    fields: dict = {}
    for key in _IMPORT_TEXT_FIELDS:
        if norm.get(key):
            fields[key] = norm[key]
    for key in _IMPORT_FLOAT_FIELDS:
        if norm.get(key):
            fields[key] = float(norm[key])
    for key in _IMPORT_BOOL_FIELDS:
        if norm.get(key):
            b = _parse_bool(norm[key])
            if b is not None:
                fields[key] = b
    if norm.get("property_type"):
        try:
            fields["property_type"] = PropertyType(norm["property_type"].lower())
        except ValueError:
            pass
    if norm.get("status"):
        try:
            fields["status"] = LeadStatus(norm["status"].lower())
        except ValueError:
            pass
    if norm.get("qualification_score"):
        fields["qualification_score"] = max(0, min(100, int(float(norm["qualification_score"]))))
    return fields


@router.post("/import", response_model=LeadImportResult)
async def import_leads(
    file: UploadFile = File(..., description="CSV with at least a phone_number column"),
    user: CurrentUser = Depends(require_role(UserRole.agent)),
    session: AsyncSession = Depends(get_db),
) -> LeadImportResult:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Expected a .csv file")

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded") from None

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or not any(
        (f or "").strip().lower() == "phone_number" for f in reader.fieldnames
    ):
        raise HTTPException(status_code=400, detail="CSV must contain a 'phone_number' column")

    repo = LeadRepository(session)
    created = updated = skipped = 0
    errors: list[LeadImportError] = []

    # Row 1 is the header, so data rows start at 2.
    for i, row in enumerate(reader, start=2):
        phone = (row.get("phone_number") or row.get("Phone_Number") or "").strip().replace(" ", "")
        if not _E164_ok(phone):
            skipped += 1
            errors.append(LeadImportError(row=i, error="missing/invalid phone_number"))
            continue
        try:
            fields = _parse_row(row)
        except (ValueError, TypeError) as exc:
            skipped += 1
            errors.append(LeadImportError(row=i, error=f"parse error: {exc}"))
            continue

        existing = await repo.get_by_phone(phone, tenant_id=user.tenant_id)
        await repo.upsert_by_phone(
            phone, tenant_id=user.tenant_id, source=LeadSource.csv_import, **fields
        )
        if existing is None:
            created += 1
        else:
            updated += 1

    log.info(
        "leads.import",
        tenant=str(user.tenant_id),
        created=created,
        updated=updated,
        skipped=skipped,
    )
    return LeadImportResult(created=created, updated=updated, skipped=skipped, errors=errors)


def _E164_ok(phone: str) -> bool:
    import re

    return bool(re.match(r"^\+?[1-9]\d{7,14}$", phone))


# --------------------------------------------------------------------------- #
# Detail / update / delete
# --------------------------------------------------------------------------- #
@router.get("/{lead_id}", response_model=LeadDetailResponse)
async def get_lead(
    lead_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> LeadDetailResponse:
    lead = await LeadRepository(session).get(lead_id, tenant_id=user.tenant_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    calls = await CallRepository(session).list_for_lead(lead_id)
    appts = await AppointmentRepository(session).list_for_lead(lead_id)
    base = LeadResponse.model_validate(lead).model_dump()
    return LeadDetailResponse(
        **base,
        calls=[CallSummaryItem.model_validate(c) for c in calls],
        appointments=[AppointmentItem.model_validate(a) for a in appts],
    )


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead_endpoint(
    lead_id: uuid.UUID,
    payload: LeadUpdate,
    user: CurrentUser = Depends(require_role(UserRole.agent)),
    session: AsyncSession = Depends(get_db),
) -> LeadResponse:
    repo = LeadRepository(session)
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    row = await repo.update(lead_id, tenant_id=user.tenant_id, **fields)
    if row is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    log.info("leads.update", tenant=str(user.tenant_id), id=str(lead_id))
    return LeadResponse.model_validate(row)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead_endpoint(
    lead_id: uuid.UUID,
    user: CurrentUser = Depends(require_role(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
) -> None:
    ok = await LeadRepository(session).delete(lead_id, tenant_id=user.tenant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Lead not found")
    log.info("leads.delete", tenant=str(user.tenant_id), id=str(lead_id))
