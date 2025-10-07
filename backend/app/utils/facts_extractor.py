"""
Lightweight fact extractor for news articles
Extracts numeric facts and events before LLM processing
"""
import re
from typing import List, Dict, Any, Set
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FactsExtractor:
    """Extract structured facts from news article text"""

    # Event type patterns
    EVENT_PATTERNS = {
        "EARNINGS": r"\bearnings?\b|\beps\b|\bprofit\b|\brevenue\b|\bquarter(?:ly)?\b",
        "GUIDANCE": r"\bguidance\b|\bforecast\b|\boutlook\b|\bexpect(?:s|ations)?\b|\bproject(?:s|ions)?\b",
        "PRICE_CUT": r"\bprice cut\b|\breduces? price\b|\bcheaper\b|\bdiscount\b|\blower(?:s|ed)? price\b",
        "PRODUCT_LAUNCH": r"\blaunches?\b|\bannounces?\b|\bunveils?\b|\bintroduces?\b|\bnew product\b|\bnew model\b",
        "REGULATORY": r"\bregulator(?:y|s)?\b|\bsec\b|\bftc\b|\blawsuit\b|\binvestigation\b|\bfine\b",
        "MACRO": r"\binterest rate\b|\binflation\b|\bfed(?:eral reserve)?\b|\bgdp\b|\bunemployment\b",
        "PARTNERSHIP": r"\bpartnership\b|\bdeal\b|\bagreement\b|\bcollaboration\b|\bacquisition\b|\bmerger\b",
        "LAYOFFS": r"\blayoffs?\b|\bjob cuts?\b|\breduction in force\b|\bdownsizing\b"
    }

    # Numeric patterns
    NUMERIC_PATTERNS = {
        "percentage": r"([-+]?\d+\.?\d*)\s*%",
        "currency": r"\$\s*([\d,]+\.?\d*)\s*([BMK]?)",
        "units": r"([\d,]+\.?\d*)\s*(million|billion|thousand|units?|shares?)",
        "price_level": r"(?:price|stock|shares?)\s+(?:at|to|of)\s+\$\s*([\d,]+\.?\d*)",
    }

    def extract_facts(
        self,
        articles: List[Dict[str, Any]],
        max_facts: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Extract structured facts from articles

        Args:
            articles: List of news articles with title/summary
            max_facts: Maximum number of facts to return

        Returns:
            List of fact dicts with type, value, unit, source_id
        """
        facts = []
        seen_facts = set()  # Dedup similar facts

        for article in articles:
            article_id = article.get("id", "unknown")
            text = f"{article.get('title', '')} {article.get('summary', '')}"

            # Extract numeric facts
            numeric_facts = self._extract_numeric_facts(text, article_id)
            for fact in numeric_facts:
                fact_key = f"{fact['type']}_{fact['value']}_{fact.get('unit', '')}"
                if fact_key not in seen_facts:
                    facts.append(fact)
                    seen_facts.add(fact_key)

            # Extract event facts
            event_facts = self._extract_event_facts(text, article_id)
            for fact in event_facts:
                fact_key = f"{fact['type']}_{fact['text'][:50]}"
                if fact_key not in seen_facts:
                    facts.append(fact)
                    seen_facts.add(fact_key)

            if len(facts) >= max_facts:
                break

        return facts[:max_facts]

    def _extract_numeric_facts(
        self,
        text: str,
        source_id: str
    ) -> List[Dict[str, Any]]:
        """Extract numeric facts from text"""
        facts = []

        # Percentages
        for match in re.finditer(self.NUMERIC_PATTERNS["percentage"], text, re.IGNORECASE):
            value = match.group(1)
            context = text[max(0, match.start() - 30):match.end() + 30]
            facts.append({
                "type": "numeric",
                "subtype": "percentage",
                "value": float(value),
                "unit": "%",
                "text": f"{value}% - {context.strip()}",
                "source_id": source_id
            })

        # Currency amounts
        for match in re.finditer(self.NUMERIC_PATTERNS["currency"], text, re.IGNORECASE):
            value = match.group(1).replace(",", "")
            multiplier = match.group(2).upper()

            # Convert to base value
            mult_map = {"B": 1e9, "M": 1e6, "K": 1e3}
            numeric_value = float(value) * mult_map.get(multiplier, 1)

            context = text[max(0, match.start() - 30):match.end() + 30]
            facts.append({
                "type": "numeric",
                "subtype": "currency",
                "value": numeric_value,
                "unit": "USD",
                "text": f"${value}{multiplier} - {context.strip()}",
                "source_id": source_id
            })

        # Units (million/billion)
        for match in re.finditer(self.NUMERIC_PATTERNS["units"], text, re.IGNORECASE):
            value = match.group(1).replace(",", "")
            unit = match.group(2).lower()

            context = text[max(0, match.start() - 30):match.end() + 30]
            facts.append({
                "type": "numeric",
                "subtype": "units",
                "value": float(value),
                "unit": unit,
                "text": f"{value} {unit} - {context.strip()}",
                "source_id": source_id
            })

        return facts

    def _extract_event_facts(
        self,
        text: str,
        source_id: str
    ) -> List[Dict[str, Any]]:
        """Extract event-based facts from text"""
        facts = []

        for event_type, pattern in self.EVENT_PATTERNS.items():
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches:
                # Take first match for this event type
                match = matches[0]
                context = text[max(0, match.start() - 50):min(len(text), match.end() + 100)]

                facts.append({
                    "type": "event",
                    "subtype": event_type,
                    "text": context.strip(),
                    "source_id": source_id
                })

        return facts

    def detect_disagreements(
        self,
        articles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect conflicting information across articles

        Returns:
            List of disagreement dicts with what/details
        """
        disagreements = []

        # Simple heuristic: look for contradicting words in similar contexts
        contradiction_pairs = [
            (r"\b(up|increase|rise|gain)", r"\b(down|decrease|fall|loss)"),
            (r"\b(bullish|optimistic|positive)", r"\b(bearish|pessimistic|negative)"),
            (r"\b(upgrade|outperform)", r"\b(downgrade|underperform)"),
        ]

        texts = [f"{a.get('title', '')} {a.get('summary', '')}" for a in articles]

        for pattern_a, pattern_b in contradiction_pairs:
            has_a = any(re.search(pattern_a, text, re.IGNORECASE) for text in texts)
            has_b = any(re.search(pattern_b, text, re.IGNORECASE) for text in texts)

            if has_a and has_b:
                disagreements.append({
                    "what": "directional_sentiment",
                    "details": f"Articles contain conflicting directional indicators"
                })

        return disagreements


def extract_facts_from_articles(
    articles: List[Dict[str, Any]],
    max_facts: int = 10
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Convenience function to extract facts and disagreements

    Returns:
        (facts, disagreements)
    """
    extractor = FactsExtractor()
    facts = extractor.extract_facts(articles, max_facts=max_facts)
    disagreements = extractor.detect_disagreements(articles)
    return facts, disagreements
