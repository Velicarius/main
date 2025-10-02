// Переключатель периода для фильтрации данных
export type Period = "7d" | "1m" | "3m" | "1y";

export type PeriodSwitcherProps = {
  value: Period;
  onChange: (period: Period) => void;
};

export function PeriodSwitcher({ value, onChange }: PeriodSwitcherProps) {
  const periods: { value: Period; label: string }[] = [
    { value: "7d", label: "7d" },
    { value: "1m", label: "1m" },
    { value: "3m", label: "3m" },
    { value: "1y", label: "1y" }
  ];

  return (
    <div className="flex bg-gray-100 rounded-lg p-1">
      {periods.map((period) => (
        <button
          key={period.value}
          onClick={() => onChange(period.value)}
          className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
            value === period.value
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-600 hover:text-gray-900"
          }`}
        >
          {period.label}
        </button>
      ))}
    </div>
  );
}
