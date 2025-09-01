"""
Agent de recherche web minimal utilisant Mistral AI (web_search connector)
"""

import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv
from mistralai import Mistral

load_dotenv()

@dataclass
class AgentResponse:
    query: str
    synthesis: str
    sources: List[str]

class WebSearchAgent:
    def __init__(self):
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY manquant dans .env")
        self.client = Mistral(api_key=api_key)
        self.model = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
        self.system = (
            "Tu es un agent qui recherche sur le web et produit une synthèse claire avec des sources."
        )

    def _ensure_agent(self) -> str:
        agent_id = os.getenv("MISTRAL_AGENT_ID")
        if agent_id:
            return agent_id
        ag = self.client.beta.agents.create(
            model=self.model,
            name="WebSearch Agent",
            description="Agent minimal avec connecteur web_search",
            instructions=self.system,
            tools=[{"type": "web_search"}],
            completion_args={"temperature": 0.3, "top_p": 0.95},
        )
        with open(".env", "a", encoding="utf-8") as f:
            f.write(f"\nMISTRAL_AGENT_ID={ag.id}\n")
        return ag.id

    def render_template(self, template: str, variables: dict) -> str:
        """Remplace les {{var}} dans template par les valeurs fournies (remplacement simple)."""
        out = template
        if variables:
            for k, v in variables.items():
                out = out.replace(f"{{{{{k}}}}}", str(v))
        return out

    def search_with_prompt(self, base_query: str, prompt_template: str, variables: dict | None = None) -> AgentResponse:
        """Recherche en utilisant un prompt personnalisé (template + variables)."""
        agent_id = self._ensure_agent()
        rendered = self.render_template(prompt_template, variables or {})
        # Ajouter le sujet si fourni
        user_prompt = rendered
        if base_query:
            user_prompt += f"\n\nSujet de recherche: {base_query}"
        resp = self.client.beta.conversations.start(agent_id=agent_id, inputs=user_prompt)

        synthesis_parts: List[str] = []
        sources: List[str] = []
        for out in resp.outputs:
            if getattr(out, "type", "") == "message.output":
                for c in getattr(out, "content", []):
                    t = getattr(c, "type", "")
                    if t == "text":
                        synthesis_parts.append(getattr(c, "text", ""))
                    elif t == "tool_reference":
                        title = getattr(c, "title", None)
                        url = getattr(c, "url", None)
                        if url:
                            sources.append(f"{title} - {url}" if title else url)
        return AgentResponse(query=base_query, synthesis="".join(synthesis_parts), sources=list(dict.fromkeys(sources)))

    def search_and_summarize(self, query: str, context: str = "") -> AgentResponse:
        agent_id = self._ensure_agent()
        user_prompt = f"{query}\n\n{('Contexte: ' + context) if context else ''}"
        resp = self.client.beta.conversations.start(agent_id=agent_id, inputs=user_prompt)

        synthesis_parts: List[str] = []
        sources: List[str] = []
        for out in resp.outputs:
            if getattr(out, "type", "") == "message.output":
                for c in getattr(out, "content", []):
                    t = getattr(c, "type", "")
                    if t == "text":
                        synthesis_parts.append(getattr(c, "text", ""))
                    elif t == "tool_reference":
                        title = getattr(c, "title", None)
                        url = getattr(c, "url", None)
                        if url:
                            sources.append(f"{title} - {url}" if title else url)
        return AgentResponse(query=query, synthesis="".join(synthesis_parts), sources=list(dict.fromkeys(sources)))
