"""
API minimale FastAPI pour l'agent de recherche web Mistral
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
import uvicorn
from agent import WebSearchAgent
from fastapi.responses import JSONResponse

app = FastAPI(title="WebSearch Agent", version="1.0")
agent = None

class BriefRequest(BaseModel):
    specialite: str
    frequence: str
    format_brief: str
    type_contenu: str
    style: str
    thematiques: List[str]
    medicaments: str
    recommandations: str
    formation_continue: str
    tendances_sante_publique: str
    limite: int
    tonalite: str

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

@app.post("/brief", response_model=SearchResponse)
async def brief(req: BriefRequest):
    if not agent:
        raise HTTPException(503, "Agent non initialisé")
    prompt_template = (
        "Tu es un assistant spécialisé en résumé médical pour les médecins généralistes.\n"
        "Ta mission est de créer un \"Brief Médical Flash\" quotidien pour le Dr. Marie Dubois.\n\n"
        "⚙️ Contexte utilisateur :\n"
        "Spécialité / Domaines d’intérêt : {{specialite}}\n"
        "Fréquence souhaitée du brief : {{frequence}}\n"
        "Format préféré du brief : {{format_brief}}\n"
        "Type de contenu à privilégier : {{type_contenu}}\n"
        "Style préféré : {{style}}\n"
        "Thématiques prioritaires : {{thematiques}}\n"
        "Préférences pour la veille sur les médicaments : {{medicaments}}\n"
        "Recommandations officielles : {{recommandations}}\n"
        "Intérêt pour la formation continue : {{formation_continue}}\n"
        "Intérêt pour le suivi des tendances santé publique : {{tendances_sante_publique}}\n\n"
        "🎯 Objectif :\n"
        "Générer un résumé médical de la journée en lien avec les sources officielles (HAS, sociétés savantes, PubMed, autorités de santé).\n"
        "Toujours inclure les sources (lien ou référence).\n"
        "Limiter le résumé à {{limite}} mots maximum pour rester lisible en moins de 5 minutes.\n"
        "Présenter les résultats sous forme de {{style}} avec une tonalité {{tonalite}}.\n"
        "Inclure une section finale “À appliquer demain en consultation” avec 2–3 points pratiques.\n\n"
        "⚠️ Contraintes :\n"
        "Pas de conseils hors cadre médical officiel.\n"
        "Ne jamais inventer de sources.\n"
        "Transparence totale : afficher la date et la référence de chaque recommandation ou étude.\n"
        "Si aucune actualité pertinente n’est trouvée, répondre : “Pas de nouveauté significative aujourd’hui. Voir dernier brief.”"
    )
    variables = req.dict()
    variables["thematiques"] = ", ".join(req.thematiques)
    res = agent.search_with_prompt(
        base_query="Résumé médical du jour",
        prompt_template=prompt_template,
        variables=variables
    )
    # Retourne la réponse formatée en JSON complet
    return JSONResponse(content={
        "query": res.query,
        "synthesis": res.synthesis,
        "sources": res.sources
    })

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
