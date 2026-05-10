# Tender Domain Model

## Source Files

- `tenderland_molecular_diagnostics_keywords.md`
- `tenderland_analytical_instruments_keywords.md`
- `molecular_diagnostics_supplier_products_table_v2.md`

These files are treated as source knowledge. The service should gradually convert them into structured dictionaries, not hand-edit the matching logic forever.

## Candidate Fields

- `source`: Tenderland, zakupki.gov.ru, manual import, etc.
- `external_id`: source-specific tender ID.
- `source_url`: link to source tender.
- `title`
- `description`
- `customer`
- `region`
- `deadline_at`
- `budget_amount`
- `currency`
- `raw_payload`

## Classification Output

- `category`: top-level category.
- `score`: normalized relevance score.
- `matched_terms`: terms that contributed to the score.
- `confidence`: low, medium, high.
- `route`: reject, watchlist, task, opportunity.
- `reason`: short human-readable explanation.

## Routing Rules

- `score >= 70`: create/update CRM opportunity.
- `40 <= score < 70`: create analyst review task.
- `20 <= score < 40`: keep in watchlist.
- `score < 20`: reject unless manually pinned.

## Deduplication Keys

Preferred order:

1. Source external ID.
2. Source URL.
3. Normalized title + customer + deadline.
4. Document hash when attachments are available.

