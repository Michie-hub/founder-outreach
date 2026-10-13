from fastapi import FastAPI
from pydantic import BaseModel, HttpUrl
from ddgs import DDGS

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
    query = (
        f"{criteria.role} startup founder" 
        f"{criteria.industry} company {criteria.country}"
    )    
    
    with DDGS() as search:
        results = search.text(query, max_results=5)
    
    return {
        "query": query,
        "results": results,
    }    
    