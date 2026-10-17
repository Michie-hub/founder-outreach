from fastapi import FastAPI, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, HttpUrl
from ddgs import DDGS
import re
from urllib.parse import urlparse
import models
from database import Base, SessionLocal, engine
from contextlib import asynccontextmanager
from typing import Literal
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")

class Founder(BaseModel):
    name: str
    company:str
    role: str
    profile_url: HttpUrl | None = None
    source_url: HttpUrl | None = None

class SearchCriteria(BaseModel):
    country: str = Field(min_length=2, max_length=100)
    industry: str = Field(min_length=2, max_length=100)
    role: str = "Founder"
    max_results: int = Field(default=20, ge=1, le=50)

class SearchResult(BaseModel):
    title: str
    url: HttpUrl
    snippet: str

class FounderCandidate(BaseModel):
    name: str | None = None
    company: str | None = None
    role: str | None = None
    profile_url: HttpUrl | None = None
    source_url: HttpUrl
    evidence: str
    review_status: Literal["needs_review", "approved", "rejected"] = "needs_review"

class FounderResponse(FounderCandidate):
    id: int
    outreach_status: str = "not_contacted"
    outreach_draft: str | None = None

class ReviewUpdate(BaseModel):
    review_status: Literal["approved", "rejected"]


class OutreachUpdate(BaseModel):
    outreach_status: Literal[
        "not_contacted", "contacted", "replied", "not_interested", "meeting_booked"
    ]


class OutreachDraftUpdate(BaseModel):
    draft: str | None = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def is_relevant_result(result: SearchResult) -> bool:
    text = f"{result.title} {result.snippet}".casefold()
    excluded_phrases = (
        "find a co-founder", "co-founder directory", "founder directory",
        "category:", "meet the team", "media platform", "company profile",
        "stock price", "shareholders", "list of", "top 10", "seven founders",
        "founders dish about their journey", "founder jobs", "hire a founder",
    )
    if any(phrase in text for phrase in excluded_phrases):
        return False

    return bool(re.search(
        r"\b(?:co[- ]?founder|founder|founding CEO|CEO|chief executive officer)\b",
        text,
        re.IGNORECASE,
    ))

def score_result(result: SearchResult) ->int:
    text = f"{result.title} {result.snippet}".lower()
    score = 0

    if "founder" in text:
        score += 3

    if re.search(r"\bco[- ]?founder\b", text):
        score += 3

    if "ceo" in text:
        score += 2

    if "startup" in text or "start-up" in text:
        score += 2

    if "linkedin.com/in/" in str(result.url):
        score += 3

    parsed = parse_founder_candidate(result)
    if parsed.name:
        score += 2
    if parsed.company:
        score += 2

    if not parsed.name:
        score -= 1
    return score

def display_candidate(result: SearchResult) -> dict:
    return {
        "title": result.title,
        "source_url": str(result.url),
        "evidence": result.snippet,
    }


def is_likely_person_name(value: str | None) -> bool:
    if not value:
        return False
    words = value.strip().split()
    if not 2 <= len(words) <= 4 or len(value) > 80:
        return False
    if words[0].casefold() in {
        "a", "an", "the", "meet", "inside", "how", "what", "why",
        "top", "best", "canada", "canadian", "founder", "co-founder",
        "october", "summary", "profile",
    }:
        return False
    return all(
        re.fullmatch(r"[A-Z](?:[\w.'’\-]+)?", word) is not None
        and (len(word) == 1 or any(character.islower() for character in word))
        for word in words
    )


def extract_name_from_evidence(evidence: str, source_url: str | None = None) -> str | None:
    leading_name = re.search(
        r"^([A-Z](?:[\w.'’\-]+)?(?:\s+[A-Z](?:[\w.'’\-]+)?){1,3})"
        r"(?=\s+(?i:is|was|interview|profile|founder|co-founder|CEO|"
        r"story|biography|joins|named|\())",
        evidence.strip(),
    )
    if leading_name and is_likely_person_name(leading_name.group(1)):
        return leading_name.group(1).strip()

    profile_name = re.search(
        r"\bView\s+([A-Z](?:[\w.'’\-]+)?(?:\s+[A-Z](?:[\w.'’\-]+)?){1,3})['’]s\s+profile\b",
        evidence,
    )
    if profile_name and is_likely_person_name(profile_name.group(1)):
        return profile_name.group(1).strip()

    if source_url:
        parsed_url = urlparse(source_url)
        path = parsed_url.path.strip("/")
        parts = path.split("/")
        is_profile_path = (
            len(parts) == 2 and parts[0].casefold() in {"in", "person", "wiki"}
        ) or parsed_url.netloc.casefold().endswith("publicprofile.com")
        if is_profile_path and parts:
            slug = re.sub(r"-[0-9a-f]{4,}$", "", parts[-1], flags=re.IGNORECASE)
            slug_name = re.sub(r"[_-]+", " ", slug)
            if is_likely_person_name(slug_name.title()):
                return slug_name.title()
    return None

def parse_founder_candidate(
    result: SearchResult,
) -> FounderCandidate:
    title = re.sub(r"\s+", " ", result.title).strip()
    snippet = re.sub(r"\s+", " ", result.snippet).strip()

    name = None
    company = None
    role = None

    role_pattern = (
        r"(?:president\s*(?:&|and)\s*founder|"
        r"founder\s*(?:&|and)\s*president|"
        r"co[- ]?founder(?:\s*(?:&|and)\s*(?:CEO|chief executive officer))?|"
        r"founder(?:\s*(?:&|and)\s*(?:CEO|chief executive officer))?|"
        r"CEO\s*(?:&|and)\s*founder|"
        r"founding CEO|CEO|chief executive officer)"
    )
    title_patterns = (
        rf"^(.+?)\s+[-–—]\s+({role_pattern})\s+(?:at|@|of)\s+(.+?)\s*$",
        rf"^([^|]+?)\s*\|\s*({role_pattern})\s*[-–—,:]\s*([^|]+)",
        rf"^(.+?)\s*,\s*({role_pattern})\s+(?:at|@|of)\s+(.+?)\s*$",
        rf"^(.+?)\s+[-–—]\s+({role_pattern})\s+[-–—:]\s+(.+?)\s*$",
    )
    for pattern in title_patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match and is_likely_person_name(match.group(1).strip()):
            name, role, company = (part.strip() for part in match.groups())
            break

    # Article titles often start with a person's name and then a word such
    # as "interview", "profile", or "founder".
    if not name:
        leading_name = re.search(
            r"^([A-Z][\w'’.-]+(?:\s+[A-Z][\w'’.-]+){1,2})"
            r"(?=\s+(?i:interview|profile|founder|co-founder|CEO|story|"
            r"biography|joins|named|on|at|of)\b)",
            title,
        )
        if leading_name:
            possible_name = leading_name.group(1).strip()
            if possible_name.split()[0].casefold() not in {
                "meet", "the", "inside", "how", "what", "why", "top", "best"
            }:
                name = possible_name

    # Extract a person and company when the snippet connects them directly.
    if not name or not company:
        person_company = re.search(
            rf"\b([A-Z][\w.'’-]+(?:\s+[A-Z][\w.'’-]+){{1,3}})"
            rf"\s*(?:is|was|,)?\s*(?:the\s+)?((?i:{role_pattern}))\s+(?:at|of)\s+"
            r"([A-Z][\w&.'’ -]{1,60}?)(?=[,.;·•|(]|\s+(?:and|who|which|she|he|they|attended|has|have|is|was|works|leads)\b|$)",
            snippet,
        )
        if person_company:
            name = name or person_company.group(1).strip()
            role = role or person_company.group(2).strip()
            company = company or person_company.group(3).strip()

    # Also find role and company when a snippet says, for example,
    # "the founder and CEO of Shopify" but gives the person's name elsewhere.
    if not company:
        role_company = re.search(
            rf"\b((?i:{role_pattern}))\s+(?:at|of)\s+(?:the\s+)?"
            r"([A-Z][\w&.'’ -]{1,60}?)(?=[,.;·•|]|\s+(?:and|who|which|she|he|they|has|have|is|was|spent|built|leads|runs|based)\b|$)",
            snippet,
        )
        if role_company:
            role = role or role_company.group(1).strip()
            company = role_company.group(2).strip()

    if not company:
        founded_company = re.search(
            r"\b(?:co-founded|founded)\s+(?:the\s+)?"
            r"(?:(?:software|technology|tech|internet|quantum)\s+)?company\s+"
            r"([A-Z][\w&.'’ -]{1,60}?)(?=[,.;·•|]|\s+(?:and|which|that|has|have|is|was)\b|$)",
            snippet,
        )
        if founded_company:
            company = founded_company.group(1).strip()

    # Some articles place the name after the company description.
    if not name:
        company_person = re.search(
            r"\b(as the\s+)?(co[- ]?founder|founder)\s+of\s+"
            r"(?:the\s+)?(?:\w+\s+){0,3}company\s+"
            r"([A-Z][\w&.'’-]+)[,;].{0,100}?"
            r"(?:entrepreneur|CEO|founder)\s+"
            r"([A-Z][a-zA-Z.'’-]+(?:\s+[A-Z][a-zA-Z.'’-]+){1,3})"
            r"(?=\s+(?:is|was|has|had|works|leads|founded)\b)",
            snippet,
            re.IGNORECASE,
        )
        if company_person:
            role = role or company_person.group(2).strip()
            company = company or company_person.group(3).strip()
            name = company_person.group(4).strip()


    # Use the title to identify a role if the patterns
    # above did not identify one.
    if not role:
        text = f"{title} {snippet}"

        if re.search(r"\bco[- ]?founder\b", text, re.IGNORECASE):
            role = "Co-Founder"
        elif re.search(r"\bfounder\b", text, re.IGNORECASE):
            role = "Founder"
        elif re.search(r"\b(?:CEO|chief executive officer)\b", text, re.IGNORECASE):
            role = "CEO"

    if name:
        name = re.sub(
            r"\s*[|–—-]\s*(?:LinkedIn|Forbes|Crunchbase|profile).*?$",
            "",
            name,
            flags=re.IGNORECASE,
        ).strip()
    if company:
        company = re.sub(
            r"\s*[|–—]\s*(?:LinkedIn|Forbes|Crunchbase|profile).*?$",
            "",
            company,
            flags=re.IGNORECASE,
        ).strip(" ,|–—-").rstrip("& ")
    if role:
        role_aliases = {
            "founder": "Founder",
            "founder and ceo": "Founder & CEO",
            "founder & ceo": "Founder & CEO",
            "co-founder": "Co-Founder",
            "co founder": "Co-Founder",
            "co-founder and ceo": "Co-Founder & CEO",
            "co-founder & ceo": "Co-Founder & CEO",
            "ceo and founder": "CEO & Founder",
            "ceo & founder": "CEO & Founder",
            "ceo": "CEO",
            "chief executive officer": "Chief Executive Officer",
        }
        role = role_aliases.get(role.casefold(), role)

    # Only treat LinkedIn personal profile URLs as profile URLs.
    url = str(result.url)
    profile_url = (
        result.url
        if re.search(r"(?:^|\.)linkedin\.com/in/", url, re.IGNORECASE)
        else None
    )

    return FounderCandidate(
        name=name,
        company=company,
        role=role,
        profile_url=profile_url,
        source_url=result.url,
        evidence=snippet,
        review_status="needs_review",
    )


def resolve_founder_details(founder: models.Founder) -> dict:
    """Fill missing saved fields from the evidence already stored for a founder."""
    inferred = None
    if founder.evidence:
        try:
            inferred = parse_founder_candidate(SearchResult(
                title="",
                url=founder.source_url or "https://example.com/unknown",
                snippet=founder.evidence,
            ))
        except ValueError:
            pass

    inferred_name = inferred.name if inferred else None
    inferred_company = inferred.company if inferred else None
    inferred_role = inferred.role if inferred else None
    name = (
        inferred_name
        or extract_name_from_evidence(founder.evidence or "")
        or (founder.name if is_likely_person_name(founder.name) else None)
        or extract_name_from_evidence("", founder.source_url)
    )
    company = inferred_company or founder.company
    if company:
        company = re.split(r"\s+[|–—]\s+(?:LinkedIn|Crunchbase|Forbes|profile)\b", company, maxsplit=1, flags=re.IGNORECASE)[0]
        company = company.split(" · ", 1)[0].strip(" ,&|-–—")
        if len(company) > 100 or "]" in company:
            company = None

    return {
        "name": name,
        "company": company,
        "role": inferred_role or founder.role,
    }


@app.get("/")
def home():
    return FileResponse(
        FRONTEND_DIR / "index.html",
        headers={"Cache-Control": "no-store"},
    )



@app.post("/founders/search")
def search_founders(criteria: SearchCriteria):
    query = " ".join([
        criteria.role,
        criteria.industry,
        "startup",
        criteria.country,
        "founder profile",
    ])

    try:
        with DDGS() as search:
            raw_results = search.text(
                query,
                max_results=criteria.max_results,
            )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="The search provider could not return results. Please try again later.",
        ) from exc

    execution = [{
        "step": "search",
        "label": "Search public pages",
        "detail": f"The provider returned {len(raw_results)} pages.",
    }]

    results = []
    seen_source_urls = set()
    for item in raw_results:
        title = (item.get("title") or "").strip()
        href = (item.get("href") or "").strip()
        snippet = (item.get("body") or "").strip()
        if not title or not href or href in seen_source_urls:
            continue
        seen_source_urls.add(href)

        try:
            result = SearchResult(title=title, url=href, snippet=snippet)
        except ValueError:
            # One malformed provider result should not discard the whole search.
            continue
        if is_relevant_result(result):
            results.append(result)

    execution.append({
        "step": "filter",
        "label": "Filter for founder signals",
        "detail": f"{len(results)} pages matched founder or executive terms.",
    })

    results.sort(
            key=score_result,
            reverse=True,
        )
    execution.append({
        "step": "rank",
        "label": "Rank the strongest matches",
        "detail": f"Sorted {len(results)} relevant pages using profile and extraction signals.",
    })


    extracted_candidates = [
        parse_founder_candidate(result)
        for result in results
    ]
    candidates = [
        candidate for candidate in extracted_candidates
        if is_likely_person_name(candidate.name) and candidate.company
    ]
    omitted_count = len(extracted_candidates) - len(candidates)
    execution.append({
        "step": "extract",
        "label": "Extract profile details",
        "detail": (
            f"Prepared {len(candidates)} candidates with both a founder name and company; "
            f"left out {omitted_count} results where the provider snippet did not give enough detail."
        ),
    })

    execution.append({
        "step": "save",
        "label": "Show results for review",
        "detail": "Search results are temporary. Only founders you approve are saved to the database.",
    })

    return {
        "query": query,
        "results": candidates,
        "saved_count": 0,
        "execution": execution,
    }




@app.post("/founders", response_model=FounderResponse, status_code=201)
def save_founder(
    candidate: FounderCandidate,
    db: Session = Depends(get_db),
):
    if not is_likely_person_name(candidate.name) or not candidate.company:
        raise HTTPException(
            status_code=422,
            detail="A founder name and company are required before approval.",
        )

    # Approval is the point where a temporary search result enters SQLite.
    existing = db.query(models.Founder).filter(
        models.Founder.source_url == str(candidate.source_url)
    ).first()

    if existing:
        db_founder = existing
        db_founder.name = candidate.name
        db_founder.company = candidate.company
        db_founder.role = candidate.role
        db_founder.profile_url = str(candidate.profile_url) if candidate.profile_url else existing.profile_url
        db_founder.evidence = candidate.evidence
        db_founder.review_status = "approved"
    else:
        db_founder = models.Founder(
            name=candidate.name,
            company=candidate.company,
            role=candidate.role,
            profile_url=str(candidate.profile_url) if candidate.profile_url else None,
            source_url=str(candidate.source_url),
            evidence=candidate.evidence,
            review_status="approved",
        )
        db.add(db_founder)

    try:
        db.commit()
        db.refresh(db_founder)
    except Exception:
        db.rollback()
        raise

    return FounderResponse(
        id=db_founder.id,
        name=db_founder.name,
        company=db_founder.company,
        role=db_founder.role,
        profile_url=db_founder.profile_url,
        source_url=db_founder.source_url,
        evidence=db_founder.evidence,
        review_status=db_founder.review_status,
        outreach_status=db_founder.outreach_status,
        outreach_draft=db_founder.outreach_draft,
    )


@app.get("/founders", response_model=list[FounderResponse])
def get_founders(db: Session = Depends(get_db)):
    founders = (
        db.query(models.Founder)
        .order_by(models.Founder.id.desc())
        .all()
    )
    complete_founders = []
    for founder in founders:
        if founder.review_status != "approved":
            continue
        details = resolve_founder_details(founder)
        # Search snippets often describe a company or role without naming a
        # specific person. Keep those records out of the review queue.
        if not is_likely_person_name(details["name"]) or not details["company"]:
            continue
        complete_founders.append({
            "id": founder.id,
            **details,
            "profile_url": founder.profile_url,
            "source_url": founder.source_url,
            "evidence": founder.evidence,
            "review_status": founder.review_status,
            "outreach_status": founder.outreach_status,
            "outreach_draft": founder.outreach_draft,
        })
    return complete_founders

@app.patch("/founders/{founder_id}/review")
def update_founder_review(
    founder_id: int,
    update: ReviewUpdate,
    db: Session = Depends(get_db),
):
    founder = db.query(models.Founder).filter(
        models.Founder.id == founder_id
    ).first()

    if founder is None:
        raise HTTPException(
            status_code=404,
            detail="Founder not found",
        )

    founder.review_status = update.review_status
    db.commit()
    db.refresh(founder)

    return {
        "message": "Review status updated",
        "id": founder.id,
        "review_status": founder.review_status,
    }

@app.get("/founders/review/{status}")
def get_founders_by_review_status(
    status: Literal["needs_review", "approved", "rejected"],
    db: Session = Depends(get_db),
):
    founders = db.query(models.Founder).filter(
        models.Founder.review_status == status
    ).all()

    return founders


@app.patch("/founders/{founder_id}/outreach")
def update_outreach_status(
    founder_id: int,
    update: OutreachUpdate,
    db: Session = Depends(get_db),
):
    founder = db.query(models.Founder).filter(
        models.Founder.id == founder_id
    ).first()
    if founder is None:
        raise HTTPException(status_code=404, detail="Founder not found")

    founder.outreach_status = update.outreach_status
    db.commit()
    db.refresh(founder)
    return {"id": founder.id, "outreach_status": founder.outreach_status}


@app.post("/founders/{founder_id}/outreach-draft")
def create_outreach_draft(
    founder_id: int,
    update: OutreachDraftUpdate = Body(default=OutreachDraftUpdate()),
    db: Session = Depends(get_db),
):
    founder = db.query(models.Founder).filter(
        models.Founder.id == founder_id
    ).first()
    if founder is None:
        raise HTTPException(status_code=404, detail="Founder not found")

    if update.draft is not None:
        founder.outreach_draft = update.draft
    else:
        details = resolve_founder_details(founder)
        founder.name = details["name"]
        founder.company = details["company"]
        founder.role = details["role"]
        first_name = (details["name"] or "there").split()[0]
        if details["company"]:
            context = (
                f" I came across your work at {details['company']} and was "
                "interested in what you are building."
            )
        else:
            context = (
                " I came across your founder profile and was interested "
                "in what you are building."
            )
        founder.outreach_draft = (
            f"Hi {first_name},\n\n{context} "
            "Would you be open to a brief conversation?\n\nBest,"
        )
    db.commit()
    db.refresh(founder)
    return {"id": founder.id, "outreach_draft": founder.outreach_draft}
