// Общие типы для AI Insights компонентов

export type Position = {
  ticker: string;
  pct: number;
};

export type Tag = "Long-term" | "Speculative" | "To-Sell";

export type GroupTarget = {
  long: number;   // Long-term %
  spec: number;   // Speculative %
  sell: number;   // To-Sell %
};

export type GroupDistribution = {
  group: Tag;
  pct: number;
  tickers?: string[]; // опционально для tooltip
};

export type GroupedPositions = {
  longPct: number;
  specPct: number;
  sellPct: number;
  tickersByGroup: Record<Tag, string[]>;
};

// Утилиты для работы с группами
export function groupByTag(
  positions: Position[], 
  value: Record<string, Tag>
): GroupedPositions {
  const tickersByGroup: Record<Tag, string[]> = {
    "Long-term": [],
    "Speculative": [],
    "To-Sell": []
  };

  let longPct = 0;
  let specPct = 0;
  let sellPct = 0;

  positions.forEach(pos => {
    const tag = value[pos.ticker] || "Long-term"; // default
    tickersByGroup[tag].push(pos.ticker);
    
    switch (tag) {
      case "Long-term":
        longPct += pos.pct;
        break;
      case "Speculative":
        specPct += pos.pct;
        break;
      case "To-Sell":
        sellPct += pos.pct;
        break;
    }
  });

  return { longPct, specPct, sellPct, tickersByGroup };
}

// Нормализация целевых долей к 100%
export function normalizeTargets(value: GroupTarget): GroupTarget {
  const total = value.long + value.spec + value.sell;
  if (total === 0) {
    return { long: 33.33, spec: 33.33, sell: 33.34 }; // fallback
  }
  
  return {
    long: Math.round((value.long / total) * 100 * 100) / 100,
    spec: Math.round((value.spec / total) * 100 * 100) / 100,
    sell: Math.round((value.sell / total) * 100 * 100) / 100
  };
}
