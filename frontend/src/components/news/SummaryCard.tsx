import { useState } from 'react';

interface Scenario {
  name: string;
  horizon: string;
  narrative: string;
  watch_items: string[];
  confidence: number;
}

interface Posture {
  label: string;
  rationale: string;
  risk_level: string;
  time_horizon: string;
}

interface Fact {
  text: string;
  source_id: string;
}

interface Source {
  id: string;
  domain: string;
  published_at: string;
}

interface NewsSummary {
  ticker: string;
  window: string;
  prospects: string[];
  opportunities: string[];
  risks: string[];
  scenarios: Scenario[];
  posture: Posture;
  confidence: number;
  facts: Fact[];
  sources: Source[];
}

interface SummaryCardProps {
  summary: NewsSummary;
  cached: boolean;
  latency_ms: number;
}

export function SummaryCard({ summary, cached, latency_ms }: SummaryCardProps) {
  const [showScenarios, setShowScenarios] = useState(false);
  const [showSources, setShowSources] = useState(false);

  const getPostureBadgeColor = (label: string) => {
    if (label.includes('Accumulate')) return 'bg-green-500/20 text-green-400 border-green-500/30';
    if (label.includes('Avoid')) return 'bg-red-500/20 text-red-400 border-red-500/30';
    return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
  };

  const getRiskBadgeColor = (level: string) => {
    if (level === 'High') return 'bg-red-500/20 text-red-400 border-red-500/30';
    if (level === 'Low') return 'bg-green-500/20 text-green-400 border-green-500/30';
    return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 70) return 'text-green-400';
    if (confidence >= 40) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="bg-gradient-to-br from-slate-800/70 to-slate-900/70 border-2 border-blue-500/30 rounded-xl p-6 backdrop-blur-sm shadow-lg">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h2 className="text-2xl font-bold text-white">{summary.ticker} AI Brief</h2>
            <span className={`px-3 py-1 rounded-lg border text-sm font-medium ${getPostureBadgeColor(summary.posture.label)}`}>
              {summary.posture.label}
            </span>
          </div>
          <p className="text-slate-400 text-sm">
            {summary.window} window • {summary.sources.length} sources •
            <span className={`ml-1 font-semibold ${getConfidenceColor(summary.confidence)}`}>
              {summary.confidence}% confidence
            </span>
            {cached && <span className="ml-2 text-blue-400">⚡ Cached</span>}
            {!cached && <span className="ml-2 text-slate-500">({latency_ms}ms)</span>}
          </p>
        </div>
      </div>

      {/* Posture */}
      <div className="mb-6 p-4 bg-slate-700/30 rounded-lg border border-slate-600/30">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm font-semibold text-slate-300">Posture Assessment:</span>
          <span className={`px-2 py-0.5 rounded text-xs border ${getRiskBadgeColor(summary.posture.risk_level)}`}>
            {summary.posture.risk_level} Risk
          </span>
          <span className="text-xs text-slate-400">• {summary.posture.time_horizon}</span>
        </div>
        <p className="text-slate-200 text-sm leading-relaxed">{summary.posture.rationale}</p>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {/* Prospects */}
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
          <h3 className="text-green-400 font-semibold mb-3 flex items-center gap-2">
            <span>✓</span> Prospects
          </h3>
          {summary.prospects.length > 0 ? (
            <ul className="space-y-2">
              {summary.prospects.map((item, idx) => (
                <li key={idx} className="text-sm text-slate-300 leading-relaxed">• {item}</li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-500 text-sm italic">No prospects identified</p>
          )}
        </div>

        {/* Opportunities */}
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
          <h3 className="text-blue-400 font-semibold mb-3 flex items-center gap-2">
            <span>↗</span> Opportunities
          </h3>
          {summary.opportunities.length > 0 ? (
            <ul className="space-y-2">
              {summary.opportunities.map((item, idx) => (
                <li key={idx} className="text-sm text-slate-300 leading-relaxed">• {item}</li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-500 text-sm italic">No opportunities identified</p>
          )}
        </div>

        {/* Risks */}
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
          <h3 className="text-red-400 font-semibold mb-3 flex items-center gap-2">
            <span>⚠</span> Risks
          </h3>
          {summary.risks.length > 0 ? (
            <ul className="space-y-2">
              {summary.risks.map((item, idx) => (
                <li key={idx} className="text-sm text-slate-300 leading-relaxed">• {item}</li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-500 text-sm italic">No risks identified</p>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3 mb-4">
        <button
          onClick={() => setShowScenarios(!showScenarios)}
          className="px-4 py-2 bg-slate-700/50 hover:bg-slate-700 text-white rounded-lg transition-colors text-sm"
        >
          {showScenarios ? 'Hide' : 'Show'} Scenarios ({summary.scenarios.length})
        </button>
        <button
          onClick={() => setShowSources(!showSources)}
          className="px-4 py-2 bg-slate-700/50 hover:bg-slate-700 text-white rounded-lg transition-colors text-sm"
        >
          {showSources ? 'Hide' : 'Show'} Sources ({summary.sources.length})
        </button>
      </div>

      {/* Scenarios Accordion */}
      {showScenarios && summary.scenarios.length > 0 && (
        <div className="mb-4 space-y-3">
          {summary.scenarios.map((scenario, idx) => (
            <div key={idx} className="bg-slate-700/30 border border-slate-600/30 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-semibold text-white">{scenario.name} Case</h4>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-slate-400">{scenario.horizon}</span>
                  <span className={`font-semibold ${getConfidenceColor(scenario.confidence)}`}>
                    {scenario.confidence}%
                  </span>
                </div>
              </div>
              <p className="text-slate-300 text-sm mb-3">{scenario.narrative}</p>
              {scenario.watch_items.length > 0 && (
                <div>
                  <p className="text-xs text-slate-400 mb-1">Watch items:</p>
                  <ul className="flex flex-wrap gap-2">
                    {scenario.watch_items.map((item, i) => (
                      <li key={i} className="text-xs bg-slate-600/30 px-2 py-1 rounded text-slate-300">
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Sources Accordion */}
      {showSources && summary.sources.length > 0 && (
        <div className="mb-4 bg-slate-700/30 border border-slate-600/30 rounded-lg p-4">
          <h4 className="font-semibold text-white mb-3">Sources</h4>
          <ul className="space-y-2">
            {summary.sources.map((source) => (
              <li key={source.id} className="text-sm text-slate-300">
                <span className="text-blue-400 font-mono">[{source.id}]</span> {source.domain} •{' '}
                <span className="text-slate-400">{new Date(source.published_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Disclaimer */}
      <div className="mt-4 pt-4 border-t border-slate-700/50">
        <p className="text-xs text-slate-500 italic">
          ⚠ Informational only, not investment advice. AI-generated analysis based on news sources.
        </p>
      </div>
    </div>
  );
}
