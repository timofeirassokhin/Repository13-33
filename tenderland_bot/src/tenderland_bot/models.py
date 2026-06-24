"""Lightweight tender row model normalised from Tenderland API JSON."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Tenderland file URL looks like:
#   https://tenderland.ru/Api/File/GetAll?entityId=TL2530006696&entityTypeId=1&apiKey=...
_ENTITY_ID_RE = re.compile(r"entityId=(TL[0-9A-Za-z_-]+)")


def _extract_entity_id(files_url: str | None) -> str | None:
    if not files_url:
        return None
    m = _ENTITY_ID_RE.search(files_url)
    return m.group(1) if m else None


def _join_str_list(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join(str(v) for v in value if v)
    return str(value)


def _customer_name(tender: dict[str, Any]) -> str:
    customers = tender.get("customers") or tender.get("lotCustomerShortName") or []
    if isinstance(customers, list):
        names: list[str] = []
        for c in customers:
            if isinstance(c, dict):
                name = c.get("lotCustomerShortName") or c.get("shortName") or c.get("fullName")
                if name:
                    names.append(str(name))
            elif isinstance(c, str):
                names.append(c)
        return "; ".join(names)
    if isinstance(customers, dict):
        return str(customers.get("lotCustomerShortName") or customers.get("shortName") or "")
    return str(customers or "")


def _etp_link(tender: dict[str, Any]) -> str:
    link = tender.get("etpLink")
    if isinstance(link, dict):
        return str(link.get("Link") or link.get("Name") or "")
    return str(link or "")


@dataclass
class TenderRow:
    """Normalised flat row for export."""

    reg_number: str
    name: str
    begin_price: float
    customer: str
    publish_date: str
    end_date: str
    region: str
    type_name: str
    categories: str
    module: str
    etp_link: str
    files_url: str
    entity_id: str | None
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    @classmethod
    def from_export_item(cls, item: dict[str, Any]) -> "TenderRow":
        tender = item.get("tender") or {}
        files_url = tender.get("files") or ""
        return cls(
            reg_number=str(tender.get("regNumber") or ""),
            name=str(tender.get("name") or "").strip(),
            begin_price=float(tender.get("beginPrice") or 0.0),
            customer=_customer_name(tender),
            publish_date=str(tender.get("publishDate") or ""),
            end_date=str(tender.get("endDate") or ""),
            region=_join_str_list(tender.get("region")),
            type_name=_join_str_list(tender.get("typeName")),
            categories=_join_str_list(tender.get("lotCategories")),
            module=_join_str_list(tender.get("module")),
            etp_link=_etp_link(tender),
            files_url=str(files_url),
            entity_id=_extract_entity_id(files_url),
            raw=tender,
        )
