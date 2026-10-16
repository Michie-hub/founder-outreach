from fastapi import FastAPI
from pydantic import BaseModel, HttpUrl
from ddgs import DDGS
import re

app = FastAPI()

class Founder(BaseModel):
    name: str
    company:str
    role: str
    profile_url: HttpUrl | None = None
    source_url: HttpUrl | None = None
    
class SearchCriteria(BaseModel):
    country: str
    industry: str
    role: str = "Founder"
    
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
    review_status: str = "needs_review"
    
def is_relevant_result(result: SearchResult) -> bool:
    text = f"{result.title} {result.snippet}".lower()
    
    irrelavant_terms = [
        "find a co-founder",
        "co-founder directory",
        "category:",
        "meet the team",
        "media platform",
        "company profile",
        "stock price",
        "shareholders",
        "list of",
        "top 10",
        "seven founders",
        "founders dish about their journey",
    ]
    
    for term in irrelavant_terms:
        if term in text:
            return False
        
    founder_terms = [
        "founder",
        "co-founder",
        "ceo",
        "chief executive officer",
    ]   
    return any(term in text for term in founder_terms) 

def score_result(result: SearchResult) ->int:
    text = f"{result.title} {result.snippet}".lower()
    score = 0
    
    if "founder" in text:
        score += 3 
        
    if "co-founder" in text:
        score += 3

    if "ceo" in text:
        score += 2
     
    if "startup" in text or "start-up" in text:
        score += 2
    
    if "linkedin.com/in/" in str(result.url):
        score += 3
    
    if "list of" in text or "seven founders" in text:
        score -= 3
    return score   

def display_candidate(result: SearchResult) -> dict:
    return {
        "title": result.title,
        "source_url": str(result.url),
        "evidence": result.snippet,
    }

def parse_founder_candidate(
    result: SearchResult,
) -> FounderCandidate:
    title = result.title.strip()
    snippet = result.snippet.strip()

    name = None
    company = None
    role = None

    # Pattern 1: "Scott Cook - Founder at Stealth Startup | LinkedIn"
    pattern_at = re.search(
        r"^(.+?)\s*[-–—]\s*"
        r"(co-founder|founder|CEO\s*(?:&|and)\s*founder)"
        r"\s+(?:at|@)\s+(.+?)"
        r"(?:\s*\|\s*.*)?$",
        title,
        re.IGNORECASE,
    )

    if pattern_at:
        name = pattern_at.group(1).strip()
        role = pattern_at.group(2).strip()
        company = pattern_at.group(3).strip()

    # Pattern 2: "Greg Smith | Founder & CEO - Thinkific | Forbes"
    if not name:
        pattern_pipe = re.search(
            r"^([^|]+?)\s*\|\s*"
            r"(founder\s*(?:&|and)\s*CEO|"
            r"CEO\s*(?:&|and)\s*founder|"
            r"co-founder|founder)"
            r"\s*[-–—]\s*([^|]+)",
            title,
            re.IGNORECASE,
        )

        if pattern_pipe:
            name = pattern_pipe.group(1).strip()
            role = pattern_pipe.group(2).strip()
            company = pattern_pipe.group(3).strip()
    
    # Pattern 3: Extract details from a sentence such as:
    # "As the founder of quantum computing company Xanadu,
    # entrepreneur Christian Weedbrook is building new machines."
    if not name:
        pattern_snippet = re.search(
            r"\b(as the founder|as the co-founder) of "
            r".{0,100}?company\s+([A-Z][\w&.-]*),\s*"
            r"(?:entrepreneur|CEO|founder)\s+"
            r"([A-Z][a-zA-Z.'-]+"
            r"(?:\s+[A-Z][a-zA-Z.'-]+){1,3})"
            r"(?=\s+(?:is|was|has|had|works|leads|founded)\b)",
            snippet,
            re.IGNORECASE,
        )

        if pattern_snippet:
            role_text = pattern_snippet.group(1).lower()
            role = (
                "Co-Founder"
                if "co-founder" in role_text
                else "Founder"
            )
            company = pattern_snippet.group(2).strip()
            name = pattern_snippet.group(3).strip()

    
    # Use the title to identify a role if the patterns
    # above did not identify one.
    if not role:
        text = f"{title} {snippet}"

        if re.search(r"\bco-founder\b", text, re.IGNORECASE):
            role = "Co-Founder"
        elif re.search(r"\bfounder\b", text, re.IGNORECASE):
            role = "Founder"
        elif re.search(r"\bCEO\b", text, re.IGNORECASE):
            role = "CEO"

    # Only treat LinkedIn personal profile URLs as profile URLs.
    url = str(result.url)
    profile_url = (
        result.url
        if "linkedin.com/in/" in url.lower()
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

         
@app.get("/")
def home():
    return {"message": "Founder Outreach API is running"}

@app.post("/founders")
def create_founder(founder: Founder):
    return {
        "message": "Founder data received successfully",
        "founder": founder,
    }

@app.post("/founders/Search")
def search_founders(criteria: SearchCriteria):
    
    query = " ".join([
        criteria.role,
        criteria.industry,
        "startup",
        criteria.country,
        "founder profile",
])
  
    with DDGS() as search:
        raw_results = search.text(query, max_results=10)
        
    results = []
    
    for item in raw_results:
        result = SearchResult(
            title=item["title"],
            url=item["href"],
            snippet=item["body"],
        )
        if is_relevant_result(result):
            results.append(result)
            
    results.sort(
            key=score_result,
            reverse=True,
        )
    return {
        "query": query,
        "results": [
            parse_founder_candidate(result)
            for result in results
            ],
    }
