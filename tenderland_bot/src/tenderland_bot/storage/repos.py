"""CRUD-репозитории под таблицы tenderland_*.

Если БД недоступна — все методы no-op возвращают None (silent fallback).
Это позволяет тому же коду гонять локально (без Postgres) и на сервере (с БД).
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Iterable, Optional

from .db import get_pool, db_available


def _conn():
    """Контекст-менеджер соединения; если БД нет — возвращает None."""
    pool = get_pool()
    if pool is None:
        return None
    return pool.connection()


# -----------------------------------------------------------------------------
# TenderRepo
# -----------------------------------------------------------------------------
class TenderRepo:
    @staticmethod
    def upsert(meta: dict, search_topic: str, search_domain: Optional[str] = None,
               run_id: Optional[int] = None) -> Optional[int]:
        """Вставка/обновление одного тендера. Возвращает id или None."""
        if not db_available():
            return None
        tender_id = meta.get("regNumber") or meta.get("tender_regNumber")
        if not tender_id:
            return None
        customers = meta.get("customers") or []
        c0 = customers[0] if customers else {}
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tenderland_tender (
                        tender_id, reg_number, name, begin_price,
                        publish_date, end_date, region, type_name,
                        customer_short, customer_full, customer_inn, customer_ogrn, customer_kpp,
                        lot_categories, module, etp_link, files_url, file_count,
                        raw_json, search_topic, search_domain, last_seen_run_id
                    )
                    VALUES (
                        %(tid)s, %(reg)s, %(name)s, %(bp)s,
                        %(pdate)s, %(edate)s, %(region)s, %(tname)s,
                        %(c_short)s, %(c_full)s, %(c_inn)s, %(c_ogrn)s, %(c_kpp)s,
                        %(cats)s, %(module)s, %(etp)s, %(furl)s, %(fcount)s,
                        %(raw)s, %(topic)s, %(domain)s, %(run_id)s
                    )
                    ON CONFLICT (tender_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        begin_price = EXCLUDED.begin_price,
                        end_date = EXCLUDED.end_date,
                        lot_categories = EXCLUDED.lot_categories,
                        file_count = EXCLUDED.file_count,
                        raw_json = EXCLUDED.raw_json,
                        last_seen_at = now(),
                        last_seen_run_id = EXCLUDED.last_seen_run_id
                    RETURNING id
                    """,
                    {
                        "tid": tender_id,
                        "reg": meta.get("regNumber") or tender_id,
                        "name": meta.get("name") or "",
                        "bp": meta.get("beginPrice"),
                        "pdate": meta.get("publishDate"),
                        "edate": meta.get("endDate"),
                        "region": meta.get("region"),
                        "tname": meta.get("typeName"),
                        "c_short": c0.get("lotCustomerShortName") or c0.get("customerShortName"),
                        "c_full": c0.get("lotCustomerFullName") or c0.get("customerFullName"),
                        "c_inn": c0.get("lotCustomerInn") or c0.get("customerInn"),
                        "c_ogrn": c0.get("lotCustomerOgrn") or c0.get("customerOgrn"),
                        "c_kpp": c0.get("lotCustomerKpp") or c0.get("customerKpp"),
                        "cats": meta.get("lotCategories") or [],
                        "module": meta.get("module"),
                        "etp": meta.get("etpLink"),
                        "furl": meta.get("files"),
                        "fcount": meta.get("fileCount"),
                        "raw": json.dumps(meta, ensure_ascii=False),
                        "topic": search_topic,
                        "domain": search_domain,
                        "run_id": run_id,
                    },
                )
                row = cur.fetchone()
                return row[0] if row else None


# -----------------------------------------------------------------------------
# RunRepo
# -----------------------------------------------------------------------------
class RunRepo:
    @staticmethod
    def start(notes: Optional[str] = None) -> Optional[int]:
        if not db_available():
            return None
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO tenderland_run (notes) VALUES (%s) RETURNING id",
                    (notes,),
                )
                return cur.fetchone()[0]

    @staticmethod
    def finish(run_id: int, *, status: str = "done",
               total_collected: Optional[int] = None,
               total_tier2_pass: Optional[int] = None,
               total_tier2_review: Optional[int] = None,
               total_tier2_drop: Optional[int] = None,
               total_tier3: Optional[int] = None,
               api_requests: Optional[int] = None,
               api_units_used: Optional[int] = None,
               llm_cost_usd: Optional[float] = None,
               llm_input_tokens: Optional[int] = None,
               llm_output_tokens: Optional[int] = None,
               error_message: Optional[str] = None) -> None:
        if not db_available() or run_id is None:
            return
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE tenderland_run SET
                        finished_at = now(),
                        status = %(status)s,
                        total_collected = COALESCE(%(tot_c)s, total_collected),
                        total_tier2_pass = COALESCE(%(t2p)s, total_tier2_pass),
                        total_tier2_review = COALESCE(%(t2r)s, total_tier2_review),
                        total_tier2_drop = COALESCE(%(t2d)s, total_tier2_drop),
                        total_tier3 = COALESCE(%(t3)s, total_tier3),
                        api_requests = COALESCE(%(req)s, api_requests),
                        api_units_used = COALESCE(%(units)s, api_units_used),
                        llm_cost_usd = COALESCE(%(cost)s, llm_cost_usd),
                        llm_input_tokens = COALESCE(%(in_t)s, llm_input_tokens),
                        llm_output_tokens = COALESCE(%(out_t)s, llm_output_tokens),
                        error_message = COALESCE(%(err)s, error_message)
                    WHERE id = %(id)s
                    """,
                    {
                        "id": run_id, "status": status,
                        "tot_c": total_collected,
                        "t2p": total_tier2_pass, "t2r": total_tier2_review, "t2d": total_tier2_drop,
                        "t3": total_tier3,
                        "req": api_requests, "units": api_units_used,
                        "cost": llm_cost_usd, "in_t": llm_input_tokens, "out_t": llm_output_tokens,
                        "err": error_message,
                    },
                )


# -----------------------------------------------------------------------------
# Tier2Repo / Tier3Repo / ArchiveRepo (заглушки + базовые операции)
# -----------------------------------------------------------------------------
class Tier2Repo:
    @staticmethod
    def upsert(run_id: int, tender_pk: int, decision) -> Optional[int]:
        """decision — Tier2Decision (pydantic)."""
        if not db_available() or run_id is None or tender_pk is None:
            return None
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tenderland_tier2_decision (
                        run_id, tender_pk, relevance, confidence, score_breakdown,
                        matched_signals, customer_class, customer_type, detected_class,
                        flags, reasoning, model, input_tokens, output_tokens, cost_usd, error
                    ) VALUES (
                        %(run)s, %(tpk)s, %(rel)s, %(conf)s, %(sb)s,
                        %(sig)s, %(cclass)s, %(ctype)s, %(dclass)s,
                        %(flags)s, %(reason)s, %(model)s, %(in_t)s, %(out_t)s, %(cost)s, %(err)s
                    )
                    ON CONFLICT (run_id, tender_pk) DO UPDATE SET
                        relevance = EXCLUDED.relevance,
                        confidence = EXCLUDED.confidence,
                        score_breakdown = EXCLUDED.score_breakdown,
                        matched_signals = EXCLUDED.matched_signals,
                        customer_class = EXCLUDED.customer_class,
                        customer_type = EXCLUDED.customer_type,
                        detected_class = EXCLUDED.detected_class,
                        flags = EXCLUDED.flags,
                        reasoning = EXCLUDED.reasoning,
                        model = EXCLUDED.model,
                        input_tokens = EXCLUDED.input_tokens,
                        output_tokens = EXCLUDED.output_tokens,
                        cost_usd = EXCLUDED.cost_usd,
                        error = EXCLUDED.error
                    RETURNING id
                    """,
                    {
                        "run": run_id, "tpk": tender_pk,
                        "rel": decision.relevance,
                        "conf": float(decision.confidence),
                        "sb": json.dumps(decision.score_breakdown.model_dump(), ensure_ascii=False),
                        "sig": list(decision.matched_signals),
                        "cclass": decision.customer_class,
                        "ctype": decision.customer_type,
                        "dclass": decision.detected_class,
                        "flags": list(decision.flags),
                        "reason": decision.reasoning,
                        "model": decision.model,
                        "in_t": decision.input_tokens,
                        "out_t": decision.output_tokens,
                        "cost": float(decision.cost_usd) if decision.cost_usd else None,
                        "err": decision.error,
                    },
                )
                row = cur.fetchone()
                return row[0] if row else None


class Tier3Repo:
    """Заглушка — будет наполнена при реализации Tier-3."""
    pass


class ArchiveRepo:
    """Заглушка — будет наполнена при Tier-3 (после скачивания zip)."""
    pass


def save_run_decisions(
    run_id: int,
    items_with_decisions: Iterable[tuple[dict, str, Optional[str], Any]],
) -> int:
    """Сохранить (meta, topic, domain, decision) пачкой. Возвращает кол-во записанных."""
    if not db_available() or run_id is None:
        return 0
    saved = 0
    for meta, topic, domain, decision in items_with_decisions:
        tpk = TenderRepo.upsert(meta, topic, domain, run_id=run_id)
        if tpk is None:
            continue
        Tier2Repo.upsert(run_id, tpk, decision)
        saved += 1
    return saved
