import { useEffect, useState } from 'react';
import { getBaseUrl } from '../lib/api';
import { useSettingsStore } from '../store/settings';
import { SummaryCard } from '../components/news/SummaryCard';

interface NewsArticle {
  id: string;
  provider: string;
  title: string;
  summary: string | null;
  url: string;
  source: string;
  tickers: string[];
  event_type: string | null;
  published_at: string;
  language: string;
}

interface ProviderMeta {
  status: string;
  count: number;
  error?: string;
  latency_ms: number | null;
}

interface NewsResponse {
  articles: NewsArticle[];
  meta: {
    total: number;
    returned: number;
    providers: Record<string, ProviderMeta>;
    cache_hit: boolean;
    latency_ms: number;
  };
}

interface NewsSummaryResponse {
  summary: any;
  cached: boolean;
  latency_ms: number;
}

export default function News() {
  const { settings } = useSettingsStore();
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [meta, setMeta] = useState<NewsResponse['meta'] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tickerFilter, setTickerFilter] = useState('');
  const [limit, setLimit] = useState(50);

  // Summary state
  const [summary, setSummary] = useState<NewsSummaryResponse | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  useEffect(() => {
    fetchNews();
  }, []);

  const fetchNews = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        limit: limit.toString()
      });

      if (tickerFilter.trim()) {
        params.set('tickers', tickerFilter.trim().toUpperCase());
      }

      const response = await fetch(`${getBaseUrl()}/news/aggregate?${params}`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch news');
      }

      const data: NewsResponse = await response.json();
      setArticles(data.articles);
      setMeta(data.meta);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch news');
    } finally {
      setLoading(false);
    }
  };

  const handleApplyFilters = () => {
    fetchNews();
    // Clear summary when filters change
    setSummary(null);
  };

  const handleGenerateSummary = async () => {
    if (!tickerFilter.trim()) {
      setSummaryError('Please enter a ticker symbol to generate summary');
      return;
    }

    const ticker = tickerFilter.trim().toUpperCase().split(',')[0]; // Use first ticker

    try {
      setSummaryLoading(true);
      setSummaryError(null);

      const response = await fetch(`${getBaseUrl()}/news/summary`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ticker: ticker,
          window_hours: 24,
          limit: 10,
          model: settings.newsAiModel,
          provider: settings.newsAiProvider
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate summary');
      }

      const data: NewsSummaryResponse = await response.json();
      setSummary(data);
    } catch (err) {
      setSummaryError(err instanceof Error ? err.message : 'Failed to generate summary');
    } finally {
      setSummaryLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getProviderBadgeColor = (provider: string) => {
    const colors: Record<string, string> = {
      finnhub: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      alphavantage: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      newsapi: 'bg-green-500/20 text-green-400 border-green-500/30'
    };
    return colors[provider] || 'bg-gray-500/20 text-gray-400 border-gray-500/30';
  };

  const getEventTypeBadge = (eventType: string | null) => {
    if (!eventType || eventType === 'general') return null;

    const colors: Record<string, string> = {
      earnings: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      'M&A': 'bg-pink-500/20 text-pink-400 border-pink-500/30'
    };

    return (
      <span className={`px-2 py-0.5 text-xs rounded border ${colors[eventType] || 'bg-gray-500/20 text-gray-400 border-gray-500/30'}`}>
        {eventType}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
          <div className="text-slate-400">Loading news...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent mb-2">
          📰 Market News
        </h1>
        <p className="text-slate-400">Aggregated news from multiple providers</p>
      </div>

      {/* Filters */}
      <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-slate-700/50 rounded-xl p-6 backdrop-blur-sm">
        <div className="flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Stock Tickers
            </label>
            <input
              type="text"
              value={tickerFilter}
              onChange={(e) => setTickerFilter(e.target.value)}
              placeholder="e.g., AAPL,TSLA,GOOGL"
              className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="w-32">
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Limit
            </label>
            <input
              type="number"
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value) || 50)}
              min="1"
              max="200"
              className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <button
            onClick={handleApplyFilters}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            Apply Filters
          </button>

          <button
            onClick={handleGenerateSummary}
            disabled={summaryLoading || !tickerFilter.trim()}
            className="px-6 py-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {summaryLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                Summarizing...
              </>
            ) : (
              <>
                <span>✨</span> Summarize with AI
              </>
            )}
          </button>
        </div>

        {/* Provider Status */}
        {meta && (
          <div className="mt-4 pt-4 border-t border-slate-700/50">
            <div className="flex flex-wrap gap-4 text-sm">
              <div className="text-slate-400">
                <span className="font-semibold text-white">{meta.returned}</span> articles
              </div>
              <div className="text-slate-400">
                <span className="font-semibold text-white">{meta.latency_ms}ms</span> latency
              </div>
              {Object.entries(meta.providers).map(([name, info]) => (
                <div key={name} className="text-slate-400">
                  <span className={`font-semibold ${info.status === 'ok' ? 'text-green-400' : 'text-red-400'}`}>
                    {name}
                  </span>
                  {': '}
                  {info.status === 'ok' ? `${info.count} articles` : `error (${info.error})`}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-gradient-to-r from-red-900/20 to-red-800/20 border border-red-500/30 rounded-xl p-6 backdrop-blur-sm">
          <div className="flex items-center space-x-3">
            <div className="w-6 h-6 bg-red-500/20 rounded-full flex items-center justify-center">
              <span className="text-red-400 text-sm">!</span>
            </div>
            <div className="text-red-400 font-medium">{error}</div>
          </div>
        </div>
      )}

      {/* Summary Error */}
      {summaryError && (
        <div className="bg-gradient-to-r from-orange-900/20 to-orange-800/20 border border-orange-500/30 rounded-xl p-4 backdrop-blur-sm">
          <div className="flex items-center space-x-3">
            <div className="w-5 h-5 bg-orange-500/20 rounded-full flex items-center justify-center">
              <span className="text-orange-400 text-xs">!</span>
            </div>
            <div className="text-orange-400 text-sm">{summaryError}</div>
          </div>
        </div>
      )}

      {/* AI Summary Card */}
      {summary && (
        <SummaryCard
          summary={summary.summary}
          cached={summary.cached}
          latency_ms={summary.latency_ms}
        />
      )}

      {/* Articles */}
      <div className="space-y-4">
        {articles.length === 0 && !error ? (
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-8 text-center">
            <p className="text-slate-400">No news articles found. Try adjusting your filters.</p>
          </div>
        ) : (
          articles.map((article) => (
            <div
              key={article.id}
              className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-slate-700/50 rounded-xl p-6 backdrop-blur-sm hover:border-slate-600/50 transition-all"
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-lg font-semibold text-white hover:text-blue-400 transition-colors"
                  >
                    {article.title}
                  </a>
                </div>
              </div>

              {/* Summary */}
              {article.summary && (
                <p className="text-slate-300 mb-4 leading-relaxed">
                  {article.summary}
                </p>
              )}

              {/* Metadata */}
              <div className="flex flex-wrap items-center gap-3 text-sm">
                {/* Provider Badge */}
                <span className={`px-3 py-1 rounded-lg border ${getProviderBadgeColor(article.provider)}`}>
                  {article.provider}
                </span>

                {/* Source */}
                <span className="text-slate-400">
                  {article.source}
                </span>

                {/* Event Type */}
                {getEventTypeBadge(article.event_type)}

                {/* Tickers */}
                {article.tickers.length > 0 && (
                  <div className="flex items-center gap-2">
                    {article.tickers.slice(0, 5).map((ticker) => (
                      <span
                        key={ticker}
                        className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded text-xs"
                      >
                        {ticker}
                      </span>
                    ))}
                  </div>
                )}

                {/* Date */}
                <span className="ml-auto text-slate-400 text-xs">
                  {formatDate(article.published_at)}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
