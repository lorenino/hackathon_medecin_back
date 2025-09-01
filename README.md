# Mistral WebSearch Agent (minimal)

Agent de recherche web basé sur l'API Mistral (connecteur `web_search`). Projet minimal: uniquement agent, API et configuration.

## 1) Prérequis
- Python 3.10+
- Clé API Mistral: https://console.mistral.ai/

## 2) Installation
```bash
pip install -r requirements.txt
```

## 3) Configuration
1. Copier le fichier d'exemple puis éditer:
```bash
cp .env.example .env
```
2. Mettre votre clé dans `.env`:
```
MISTRAL_API_KEY=VOTRE_CLE
MISTRAL_MODEL=mistral-large-latest
```
> À la première exécution, l'agent créera automatiquement un agent Mistral avec le connecteur web_search et enregistrera `MISTRAL_AGENT_ID` dans `.env`.

## 4) Test rapide (agent direct)
Exécuter une recherche simple sans lancer de serveur:
```bash
python -c "from agent import WebSearchAgent; a=WebSearchAgent(); r=a.search_and_summarize('intelligence artificielle médecine 2024'); print(r.synthesis[:500]); print('\nSources:', len(r.sources)); [print('-', s) for s in r.sources[:5]]"
```

## 5) API HTTP minimale
Lancer l'API FastAPI:
```bash
python api.py
```
Endpoints:
- `GET  /health` — statut de l'API
- `POST /search` — recherche standard avec `query` (et optionnel `context`)
- `POST /search/prompt` — recherche avec template de prompt personnalisé

Exemples:
```bash
# Healthcheck
curl http://localhost:8000/health

# Recherche simple
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"intelligence artificielle médecine 2024"}'

# Recherche avec template de prompt
curl -X POST http://localhost:8000/search/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "query": "intelligence artificielle médecine 2024",
    "prompt_template": "Tu es un assistant spécialisé en résumé médical... Limite: {{limite}} mots. Style: {{style}}.",
    "variables": {"limite": 180, "style": "bullet points", "specialite": "Médecine générale", "tonalite": "professionnelle", "medicaments": "anticoagulants", "recommandations": "HAS, ESC"}
  }'
```

## 6) Paramètres supportés
- `.env`
  - `MISTRAL_API_KEY` (obligatoire)
  - `MISTRAL_MODEL` (optionnel, défaut: `mistral-large-latest`)
  - `MISTRAL_AGENT_ID` (optionnel, auto-ajouté après création du premier agent)

## 7) Notes
- Le connecteur `web_search` est utilisé par défaut; le modèle cite des sources (URLs) dans la réponse.
- Le champ `prompt_template` accepte des variables au format `{{nom}}` (remplacement direct côté agent).
- Pour stopper l’API, interrompre le processus (Ctrl+C).



## 8) Diagrammes UML

### 8.1 Diagramme de classes (UML)
```mermaid
classDiagram
  direction LR
  class WebSearchAgent {
    - client: Mistral
    - model: str
    - system: str
    + __init__()
    + render_template(template: str, variables: dict) str
    + search_with_prompt(base_query: str, prompt_template: str, variables: dict) AgentResponse
    + search_and_summarize(query: str, context: str) AgentResponse
    - _ensure_agent() str
  }

  class AgentResponse {
    + query: str
    + synthesis: str
    + sources: List[str]
  }

  class SearchRequest {
    + query: str
    + context: Optional[str]
  }

  class PromptSearchRequest {
    + query: str
    + prompt_template: str
    + variables: Dict[str, Any]
  }

  class SearchResponse {
    + query: str
    + synthesis: str
    + sources: List[str]
  }

  class FastAPIApp {
    + POST /search(SearchRequest) SearchResponse
    + POST /search/prompt(PromptSearchRequest) SearchResponse
    + GET /health() dict
  }

  WebSearchAgent --> AgentResponse
  FastAPIApp --> WebSearchAgent : uses
  FastAPIApp ..> SearchRequest
  FastAPIApp ..> PromptSearchRequest
  FastAPIApp ..> SearchResponse
```

### 8.2 Diagramme de séquence (UML)
```mermaid
sequenceDiagram
  autonumber
  participant Client
  participant API as FastAPI API
  participant Agent as WebSearchAgent
  participant Mistral as Mistral API

  Client->>API: POST /search {query, context?}
  API->>Agent: search_and_summarize(query, context)
  Agent->>Agent: _ensure_agent()
  alt MISTRAL_AGENT_ID présent dans .env
    Agent-->>Agent: réutilise agent_id
  else manquant
    Agent->>Mistral: beta.agents.create(tools=[web_search])
    Mistral-->>Agent: agent_id
    Agent->>Agent: écrit MISTRAL_AGENT_ID dans .env
  end
  Agent->>Mistral: beta.conversations.start(agent_id, inputs)
  Mistral-->>Agent: outputs (text + tool_reference)
  Agent-->>API: AgentResponse(synthesis, sources)
  API-->>Client: {query, synthesis, sources}

  %% Variante avec template de prompt
  Client->>API: POST /search/prompt {query, prompt_template, variables}
  API->>Agent: search_with_prompt(query, template, vars)
  Agent->>Agent: _ensure_agent() (même logique)
  Agent->>Mistral: beta.conversations.start(agent_id, inputs)
  Mistral-->>Agent: outputs
  Agent-->>API: AgentResponse
  API-->>Client: JSON réponse
```


## 9) Diagramme d’optimisation de l’application (flux & coûts)
```mermaid
flowchart LR
  Client[Client] --> API[FastAPI]

  subgraph API_Layer
    API --> UseStd[search_and_summarize]
    API --> UseTpl[search_with_prompt]
  end

  subgraph Agent
    UseStd --> Ensure[_ensure_agent]
    UseTpl --> Render[render_template] --> Ensure
    Ensure --> Create[create_agent_if_needed]
    Create --> Persist[write_agent_id]
    Ensure --> Start[start_conversation]
    Start --> Parse[build_synthesis_extract_sources]
  end

  Start --> Mistral[Mistral_Agents_API]
  Mistral --> Web[Web_sources]
  Mistral --> Back[Results]

  Parse --> API

  subgraph Obs
    Metrics[metrics] -.-> Dash[dashboard]
    Cache[cache] -.-> API
  end

  API --> Client
```
