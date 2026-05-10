from dataclasses import dataclass
from enum import StrEnum
from re import sub


class Route(StrEnum):
    reject = "reject"
    watchlist = "watchlist"
    task = "task"
    opportunity = "opportunity"


@dataclass(frozen=True)
class CategoryProfile:
    key: str
    label: str
    strong_terms: tuple[str, ...]
    weak_terms: tuple[str, ...]
    exclude_terms: tuple[str, ...] = ()


CATALOGS: tuple[CategoryProfile, ...] = (
    CategoryProfile(
        key="mdx_sequencers",
        label="Molecular diagnostics: sequencers and genetic analyzers",
        strong_terms=(
            "sequencer",
            "sequencing",
            "ngs",
            "miseq",
            "nextseq",
            "novaseq",
            "dnbseq",
            "mgiseq",
            "genoscan",
            "helicon g50",
            "helicon g400",
            "salus pro",
            "r-gen",
            "sanger",
        ),
        weak_terms=(
            "flow cell",
            "cartridge",
            "pe150",
            "q30",
            "library",
            "dna",
            "rna",
        ),
        exclude_terms=("pcr", "rt-pcr", "real-time pcr"),
    ),
    CategoryProfile(
        key="mdx_consumables",
        label="Molecular diagnostics: NGS consumables and library preparation",
        strong_terms=(
            "library prep",
            "library preparation",
            "sequencing reagents",
            "reagent kit",
            "flow cell",
            "wash cartridge",
            "index kit",
            "umi",
            "adapter ligation",
        ),
        weak_terms=("ngs", "dna", "rna", "capture", "hybridization", "barcode"),
        exclude_terms=("pcr", "rt-pcr"),
    ),
    CategoryProfile(
        key="mdx_oncology_panels",
        label="Molecular diagnostics: oncology NGS panels",
        strong_terms=(
            "brca",
            "egfr",
            "kras",
            "nras",
            "braf",
            "her2",
            "msi",
            "oncoatlas",
            "helicon atlas",
            "solid tumor",
            "liquid biopsy",
        ),
        weak_terms=("panel", "target enrichment", "ngs", "ffpe", "somatic"),
    ),
    CategoryProfile(
        key="mdx_reproductive_hla_microarray",
        label="Molecular diagnostics: NIPT, PGT, HLA, microarrays",
        strong_terms=(
            "nipt",
            "pgt-a",
            "pgt-m",
            "hla",
            "microarray",
            "dna microarray",
            "beadchip",
            "iscan",
        ),
        weak_terms=("sequencing", "genotyping", "chromosomal", "array scanner"),
    ),
    CategoryProfile(
        key="analytical_instruments",
        label="Analytical instruments",
        strong_terms=(
            "hplc",
            "uhplc",
            "uplc",
            "gc-ms",
            "lc-ms",
            "icp-ms",
            "icp-oes",
            "aas",
            "uv-vis",
            "ftir",
            "chromatograph",
            "mass spectrometer",
            "agilent",
            "shimadzu",
            "waters",
            "sciex",
            "perkinelmer",
        ),
        weak_terms=("detector", "autosampler", "column thermostat", "quadrupole"),
    ),
)


def normalize_text(value: str) -> str:
    value = value.casefold()
    value = sub(r"[^a-z0-9а-яё\-\s]+", " ", value)
    return sub(r"\s+", " ", value).strip()


def score_tender(title: str, description: str = "") -> dict[str, object]:
    text = normalize_text(f"{title} {description}")
    category_scores = []

    for profile in CATALOGS:
        strong_matches = [term for term in profile.strong_terms if term in text]
        weak_matches = [term for term in profile.weak_terms if term in text]
        excluded = [term for term in profile.exclude_terms if term in text]

        score = min(100, len(strong_matches) * 25 + len(weak_matches) * 8)
        if excluded:
            score = max(0, score - 35)

        category_scores.append(
            {
                "key": profile.key,
                "label": profile.label,
                "score": score,
                "matched_terms": strong_matches + weak_matches,
                "excluded_terms": excluded,
            }
        )

    category_scores.sort(key=lambda item: item["score"], reverse=True)
    best = category_scores[0]
    route = route_for_score(int(best["score"]))

    return {
        "top_category": best,
        "all_categories": category_scores,
        "route": route,
        "confidence": confidence_for_score(int(best["score"])),
    }


def route_for_score(score: int) -> Route:
    if score >= 70:
        return Route.opportunity
    if score >= 40:
        return Route.task
    if score >= 20:
        return Route.watchlist
    return Route.reject


def confidence_for_score(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    if score >= 20:
        return "low"
    return "none"

