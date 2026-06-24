import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field

from tender_monitor.domain import CATALOGS, score_tender
from tender_monitor.settings import Settings


settings = Settings()

app = FastAPI(
    title="Gluvex Tender Monitor",
    version="0.1.0",
    description="Tender scoring and future Tenderland-to-Twenty integration service.",
)


class TenderCandidate(BaseModel):
    title: str = Field(default="", examples=["NGS sequencing reagents for MiSeq"])
    description: str = ""
    customer: str | None = None
    source_url: str | None = None


@app.get("/healthz")
def healthz() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "tender-monitor",
        "integrations_ready": settings.integrations_ready,
    }


@app.get("/categories")
def categories() -> list[dict[str, object]]:
    return [
        {
            "key": profile.key,
            "label": profile.label,
            "strong_terms_count": len(profile.strong_terms),
            "weak_terms_count": len(profile.weak_terms),
        }
        for profile in CATALOGS
    ]


@app.post("/score")
def score(candidate: TenderCandidate) -> dict[str, object]:
    result = score_tender(candidate.title, candidate.description)
    return {
        "candidate": candidate.model_dump(),
        **result,
    }


if __name__ == "__main__":
    uvicorn.run(
        "tender_monitor.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
