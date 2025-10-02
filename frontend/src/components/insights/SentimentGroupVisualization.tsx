/**
 * Компонент визуализации группировки позиций по сентименту
 */

import React from 'react';
import { SentimentGrouping, SentimentBucket, SentimentUtils } from '../../types/sentiment';

interface SentimentGroupVisualizationProps {
  grouping: SentimentGrouping;
  isLoading?: boolean;
}

export const SentimentGroupVisualization: React.FC<SentimentGroupVisualizationProps> = ({ 
  grouping, 
  isLoading = false 
}) => {
  
  if (isLoading) {
    return (
      <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
        <h3 className="text-lg font-semibold text-white mb-6">News Sentiment Analysis</h3>
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-slate-700 rounded"></div>
          <div className="h-4 bg-slate-700 rounded w-3/4"></div>
          <div className="h-4 bg-slate-700 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  const getSentimentBucketColor = (bucketName: string) => {
    switch (bucketName.toLowerCase()) {
      case 'bullish':
        return 'bg-gradient-to-r from-emerald-500 to-green-600';
      case 'bearish':
        return 'bg-gradient-to-r from-red-500 to-red-600';
      default:
        return 'bg-gradient-to-r from-yellow-500 to-orange-500';
    }
  };

  const getTopPositions = (bucket: SentimentBucket) => {
    return bucket.positions.slice(0, 3);
  };

  const isEmpty = !grouping.buckets.length || grouping.total_coverage === 0;

  if (isEmpty) {
    return (
      <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
        <h3 className="text-lg font-semibold text-white mb-6">News Sentiment Analysis</h3>
        
        <div className="text-center py-8">
          <div className="text-4xl mb-4">📰</div>
          <p className="text-slate-400 mb-2">
            {grouping.total_coverage === 0 
              ? 'Недостаточно новостей для анализа сентимента'
              : 'Sentiment анализ недоступен'
            }
          </p>
          <p className="text-sm text-slate-500">
            Требуется минимум 5 новостей для статистического анализа
          </p>
        </div>
      </div>
    );
  }

  // Сортируем корзины по весу (больший вес сверху)
  const sortedBuckets = [...grouping.buckets].sort((a, b) => b.weight_pct - a.weight_pct);

  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">News Sentiment Analysis</h3>
        <div className="text-sm text-slate-400">
          {grouping.timeframe} • {grouping.total_coverage} articles
        </div>
      </div>
      
      <div className="space-y-4">
        {/* Корзины sentiment */}
        {sortedBuckets.map((bucket) => (
          <div key={bucket.bucket_name} className="group">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-3">
                <div className={`w-3 h-3 rounded-full ${getSentimentBucketColor(bucket.bucket_name).replace('bg-gradient-to-r from-', 'bg-').split(' ')[0]}`}></div>
                <span className="font-medium text-white">
                  {bucket.bucket_name}
                </span>
                <span className="text-sm text-slate-400">
                  ({bucket.count} positions)
                </span>
              </div>
              <div className="text-sm text-slate-300 font-mono">
                {formatWeight(bucket.weight_pct)}%
              </div>
            </div>
            
            {/* Прогресс бар */}
            <div className="relative h-6 bg-slate-700/50 rounded-lg overflow-hidden">
              <div 
                className={`absolute top-0 left-0 h-full ${getSentimentBucketColor(bucket.bucket_name)} transition-all duration-1000 ease-out`}
                style={{ width: `${Math.min(100, bucket.weight_pct)}%` }}
              />
              <div className="absolute inset-0 flex items-center px-3">
                <div className="flex justify-between w-full text-xs text-white font-medium">
                  <span>{SentimentUtils.formatSentimentScore(bucket.avg_sentiment_score)}</span>
                  <span>{getTopPositions(bucket).join(', ')}</span>
                </div>
              </div>
            </div>

            {/* Детали при ховере */}
            <div className="mt-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
              <div className="text-xs text-slate-400 space-y-1">
                <div>
                  Avg Sentiment: {SentimentUtils.formatSentimentScore(bucket.avg_sentiment_score)}
                </div>
                {getTopPositions(bucket).length > 0 && (
                  <div>
                    Top Positions: {getTopPositions(bucket).join(', ')}
                    {bucket.positions.length > 3 && ` +${bucket.positions.length - 3} more`}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {/* Статистика fallback */}
        {grouping.fallback_rate > 0 && (
          <div className="mt-4 p-3 bg-slate-700/30 rounded-lg">
            <div className="flex justify-between items-center text-sm text-slate-400">
              <span>Model Reliability:</span>
              <span className={grouping.fallback_rate < 0.3 ? 'text-green-400' : 'text-yellow-400'}>
                {Math.round((1 - grouping.fallback_rate) * 100)}%
              </span>
            </div>
            {grouping.fallback_rate > 0.3 && (
              <div className="text-xs text-yellow-400 mt-1">
                ⚠ Some data using fallback model (FinBERT)
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Helper функция для форматирования веса
function formatWeight(weight: number): string {
  return weight.toFixed(1);
}
