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

### Explication du flux
- Client: l’application qui envoie les requêtes HTTP vers l’API.
- API (FastAPI): reçoit, valide, et route les requêtes vers l’agent.
- API_Layer/Validate: validation et normalisation des entrées.
- Cache: vérifie si une réponse existe déjà (clé dérivée de la requête + template + variables). En cas de hit, retourne aussitôt.
- Agent:
  - render_template: construit le prompt final à partir du template et des variables.
  - ensure_agent_id/create_agent_if_needed: garantit l’existence d’un agent Mistral configuré avec web_search.
  - start_conversation: appelle Mistral (Agents API) pour exécuter la recherche et générer la réponse.
  - parse_and_format: assemble la synthèse et extrait les sources (références/outils).
  - enforce_limits: applique une éventuelle limite (ex. nombre de mots) et formatage.
- Mistral_Agents_API/web_search_tool: effectue la recherche web et retourne des références exploitables.
- Obs (metrics/logs): points d’instrumentation pour suivre volumes, latence, erreurs, tokens, etc.

## 10) Diagramme de séquence optimisé (/search/prompt)
```mermaid
sequenceDiagram
  autonumber
  participant User as Client
  participant API
  participant Agent
  participant CacheLocal
  participant CacheShared
  participant VecDB as SimilarIndex
  participant Mistral

  User->>API: POST /search/prompt {query, template, vars}
  API->>API: validate_input
  API->>Agent: build_request_signature(query, template, vars)

  Agent->>CacheLocal: get(signature)
  alt local_hit
    CacheLocal-->>Agent: cached_response
    Agent-->>API: cached_response
  else miss_local
    Agent->>CacheShared: get(signature)
    alt shared_hit
      CacheShared-->>Agent: cached_response
      Agent-->>CacheLocal: put(signature, cached_response)
      Agent-->>API: cached_response
    else miss_shared
      Agent->>VecDB: find_similar(embedding(signature), topK=3)
      VecDB-->>Agent: similar_candidates[score]
      alt similar_above_threshold
        Agent->>Agent: adapt_result(candidate)
        Agent-->>CacheLocal: put(signature, adapted_response)
        Agent-->>CacheShared: put(signature, adapted_response)
        Agent-->>API: adapted_response
      else no_good_match
        Agent->>Agent: render_template
        Agent->>Agent: ensure_agent_id
        Agent->>Mistral: start_conversation(inputs)
        Mistral-->>Agent: outputs(text_refs)
        Agent->>Agent: parse_and_enforce_limits
        Agent-->>CacheLocal: put(signature, response)
        Agent-->>CacheShared: put(signature, response)
        Agent-->>API: response
      end
    end
  end
  API-->>User: JSON

  Note over API,Agent: metrics: tokens, latency, cache_hit_ratio
```

### Pistes d’optimisation complémentaires
- Budgetisation/cutoff: ne pas lancer LLM si coût estimé > budget (p.ex. tokens restants/jour)
- Batching: regrouper des requêtes proches en une seule conversation (mode “digest”)
- Paramètres dynamiques: ajuster temperature/top_p selon criticité clinique
- Filtrage de sources: privilégier HAS, ANSM, PubMed, ESC, ECDC, WHO
- TTL différenciés: augmenter TTL pour requêtes stables (guidelines), réduire pour actualités
- Observabilité: suivre tokens prompts/completions/connectors et p95/p99 latence

