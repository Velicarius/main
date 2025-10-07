"""
LLM-powered news summarization service
Generates structured ticker briefs from news articles
"""
import json
import hashlib
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from app.ai.openai_client import get_client, default_model
from app.schemas.news_summary import NewsSummary, Scenario, Posture, Fact, Source
from app.utils.facts_extractor import extract_facts_from_articles

logger = logging.getLogger(__name__)


class NewsLLMSummarizer:
    """Generate LLM-powered structured briefs from news articles"""

    SYSTEM_PROMPT = """You are a markets editor. Summarize multiple articles about one stock into a verifiable, neutral brief.

Rules:
- First facts, then interpretation. Do not fabricate numbers.
- Use only figures that appear in the provided `facts[]`, and cite `source_id`.
- Acknowledge disagreements explicitly.
- No trading advice. Provide a non-advisory "posture" label (Accumulate / Hold / Avoid) with rationale and horizon.
- Output valid JSON matching the provided schema. If evidence is weak, return empty arrays and set confidence ≤40.
- Be concise: 2-3 bullets per section maximum.
- For scenarios, provide Base (most likely), Bull (optimistic), and Bear (pessimistic) cases.
- Confidence scores should reflect evidence quality: strong facts = 70-90, weak/conflicting = 30-50.
"""

    def __init__(self, model: Optional[str] = None, provider: Optional[str] = None):
        self.model = model or default_model()
        self.provider = provider or ("ollama" if self.model.startswith(('llama', 'gemma', 'qwen', 'mistral', 'codellama')) else "openai")
        
        # Only initialize OpenAI client if using OpenAI
        if self.provider == "openai":
            self.client = get_client()
        else:
            self.client = None

    async def generate_summary(
        self,
        ticker: str,
        articles: List[Dict[str, Any]],
        window_hours: int = 24,
        portfolio_hint: Optional[str] = None
    ) -> NewsSummary:
        """
        Generate structured summary from news articles

        Args:
            ticker: Stock ticker symbol
            articles: List of normalized news articles
            window_hours: Time window in hours
            portfolio_hint: Optional portfolio context

        Returns:
            NewsSummary object
        """
        if not articles:
            return self._empty_summary(ticker, f"{window_hours}h")

        # Extract facts before LLM
        facts, disagreements = extract_facts_from_articles(articles, max_facts=10)

        # Prepare sources
        sources = [
            Source(
                id=article.get("id", "unknown")[:8],  # Short ID
                domain=article.get("source", "unknown"),
                published_at=article.get("published_at", datetime.now().isoformat()) if isinstance(article.get("published_at"), str) else article.get("published_at", datetime.now()).isoformat()
            )
            for article in articles[:10]  # Limit sources
        ]

        # Build user prompt
        user_prompt = self._build_user_prompt(
            ticker=ticker,
            window_hours=window_hours,
            articles=articles,
            facts=facts,
            disagreements=disagreements,
            portfolio_hint=portfolio_hint
        )

        # Call LLM
        try:
            start_time = time.time()

            if self.provider == "ollama":
                # Use Ollama for local models
                from app.routers.llm_proxy import LLMChatRequest, generate_with_ollama
                
                request = LLMChatRequest(
                    model=self.model,
                    prompt=user_prompt,
                    system=self.SYSTEM_PROMPT,
                    json_schema=None,  # We'll parse JSON manually
                    temperature=0.3,
                    max_tokens=2000
                )
                ollama_response = await generate_with_ollama(request)
                content = ollama_response["response"]
            else:
                # Use OpenAI for cloud models
                if not self.client:
                    raise RuntimeError("OpenAI client not initialized. Please set OPENAI_API_KEY environment variable.")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3,
                    max_tokens=2000
                )
                content = response.choices[0].message.content

            latency = int((time.time() - start_time) * 1000)
            logger.info(f"LLM summary generated for {ticker} using {self.provider}/{self.model} in {latency}ms")

            # Parse JSON response
            summary_dict = json.loads(content)

            # Construct NewsSummary object
            summary = NewsSummary(
                ticker=ticker,
                window=f"{window_hours}h",
                prospects=summary_dict.get("prospects", []),
                opportunities=summary_dict.get("opportunities", []),
                risks=summary_dict.get("risks", []),
                scenarios=[
                    Scenario(**s) for s in summary_dict.get("scenarios", [])
                ],
                posture=Posture(**summary_dict.get("posture", {
                    "label": "Hold/Neutral",
                    "rationale": "Insufficient data for assessment",
                    "risk_level": "Unknown",
                    "time_horizon": "N/A"
                })),
                confidence=summary_dict.get("confidence", 40),
                facts=[Fact(**f) for f in facts[:5]],  # Include top 5 facts
                sources=sources
            )

            return summary

        except Exception as e:
            logger.error(f"LLM summary generation failed for {ticker} using {self.provider}/{self.model}: {e}")
            
            # Provide more specific error messages
            if self.provider == "openai" and "OPENAI_API_KEY" in str(e):
                logger.error("OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.")
            elif self.provider == "ollama" and "Connection" in str(e):
                logger.error("Ollama not available. Please ensure Ollama is running on localhost:11434")
            
            return self._empty_summary(ticker, f"{window_hours}h")

    def _build_user_prompt(
        self,
        ticker: str,
        window_hours: int,
        articles: List[Dict[str, Any]],
        facts: List[Dict[str, Any]],
        disagreements: List[Dict[str, Any]],
        portfolio_hint: Optional[str]
    ) -> str:
        """Build user prompt from articles and facts"""

        # Format sources section
        sources_text = "\n".join([
            f"- [{a.get('id', 'unk')[:8]} | {a.get('source', 'Unknown')} | {a.get('published_at', 'N/A')}] "
            f"{a.get('title', 'No title')} — {a.get('summary', 'No summary')[:200]}"
            for a in articles[:10]
        ])

        # Format facts section
        facts_text = "\n".join([
            f"- {f.get('text', 'N/A')} ← {f.get('source_id', 'unknown')[:8]}"
            for f in facts[:10]
        ]) if facts else "No structured facts extracted."

        # Format disagreements
        disagree_text = "\n".join([
            f"- {d.get('what', 'Unknown')}: {d.get('details', 'N/A')}"
            for d in disagreements
        ]) if disagreements else "No major disagreements detected."

        portfolio_context = f"\nPortfolio context: {portfolio_hint}\n" if portfolio_hint else ""

        prompt = f"""Ticker: {ticker}
{portfolio_context}
Window: last {window_hours} hours.

Clustered sources (summaries only):
{sources_text}

Structured facts (numbers & events only):
{facts_text}

Disagreements:
{disagree_text}

Output strictly as JSON with this structure:
{{
  "prospects": ["..."],
  "opportunities": ["..."],
  "risks": ["..."],
  "scenarios": [
    {{"name":"Base","horizon":"3-6m","narrative":"...","watch_items":["..."],"confidence":68}},
    {{"name":"Bull","horizon":"3-6m","narrative":"...","watch_items":["..."],"confidence":55}},
    {{"name":"Bear","horizon":"3-6m","narrative":"...","watch_items":["..."],"confidence":57}}
  ],
  "posture": {{"label":"Hold/Neutral","rationale":"...","risk_level":"Medium","time_horizon":"1-3m"}},
  "confidence": 64
}}

Remember: Use only facts from the provided sources. Be concise and neutral."""

        return prompt

    def _empty_summary(self, ticker: str, window: str) -> NewsSummary:
        """Return empty summary when no articles available"""
        return NewsSummary(
            ticker=ticker,
            window=window,
            prospects=[],
            opportunities=[],
            risks=[],
            scenarios=[],
            posture=Posture(
                label="Hold/Neutral",
                rationale="Insufficient news data for analysis",
                risk_level="Unknown",
                time_horizon="N/A"
            ),
            confidence=0,
            facts=[],
            sources=[]
        )

    @staticmethod
    def generate_cache_key(
        ticker: str,
        window_hours: int,
        article_ids: List[str],
        model_version: str = "v1"
    ) -> str:
        """
        Generate cache key for summary

        Args:
            ticker: Stock ticker
            window_hours: Time window
            article_ids: List of article IDs
            model_version: Model version string

        Returns:
            Cache key string
        """
        # Sort article IDs for consistent hashing
        ids_sorted = sorted(article_ids)
        hash_input = f"{ticker}:{window_hours}:{','.join(ids_sorted)}:{model_version}"
        hash_digest = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        return f"LLM_SUMMARY:{ticker}:{window_hours}h:{hash_digest}"


def create_news_summarizer(model: Optional[str] = None, provider: Optional[str] = None) -> NewsLLMSummarizer:
    """Factory function to create NewsLLMSummarizer"""
    return NewsLLMSummarizer(model=model, provider=provider)
