import React from 'react';

// Двухпанельная сетка для AI Insights
// ЛЕВО: sticky форма управления, ПРАВО: скроллируемые результаты
type InsightsSplitProps = {
  left: React.ReactNode;  // форма/управление
  right: React.ReactNode; // результаты
};

export function InsightsSplit({ left, right }: InsightsSplitProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-screen">
      {/* ЛЕВАЯ ПАНЕЛЬ - Sticky форма управления */}
      <div className="lg:col-span-4 xl:col-span-5">
        <div className="sticky top-4 space-y-6">
          {/* Зачем sticky: форма всегда видна при скролле результатов */}
          {left}
        </div>
      </div>

      {/* ПРАВАЯ ПАНЕЛЬ - Скроллируемые результаты */}
      <div className="lg:col-span-8 xl:col-span-7">
        <div className="space-y-6">
          {/* Зачем отдельный скролл: результаты могут быть длинными, форма остается видимой */}
          {right}
        </div>
      </div>
    </div>
  );
}
