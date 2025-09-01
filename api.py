"""
API minimale FastAPI pour l'agent de recherche web Mistral
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
import uvicorn
from agent import WebSearchAgent

app = FastAPI(title="WebSearch Agent", version="1.0")
agent = None

class SearchRequest(BaseModel):
    query: str
    context: Optional[str] = ""

class PromptSearchRequest(BaseModel):
    query: str
    prompt_template: str
    variables: Optional[Dict[str, Any]] = None

class SearchResponse(BaseModel):
    query: str
    synthesis: str
    sources: List[str]

@app.on_event("startup")
async def startup_event():
    global agent
    try:
        agent = WebSearchAgent()
    except Exception as e:
        agent = None
        print(f"Startup error: {e}")

@app.get("/health")
async def health():
    return {"status": "healthy" if agent else "unhealthy"}

@app.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    if not agent:
        raise HTTPException(503, "Agent non initialisé")
    try:
        res = agent.search_and_summarize(req.query, req.context or "")
        return SearchResponse(query=res.query, synthesis=res.synthesis, sources=res.sources)
    except Exception as e:
        raise HTTPException(500, f"Erreur: {e}")

@app.post("/search/prompt", response_model=SearchResponse)
async def search_with_prompt(req: PromptSearchRequest):
    if not agent:
        raise HTTPException(503, "Agent non initialisé")
    try:
        res = agent.search_with_prompt(req.query, req.prompt_template, req.variables or {})
        return SearchResponse(query=res.query, synthesis=res.synthesis, sources=res.sources)
    except Exception as e:
        raise HTTPException(500, f"Erreur: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
