// Карточка KPI с крупным значением, подписью и иконкой
export type KpiTileProps = {
  label: string;
  value: string;            // уже отформатированный
  sub?: string;             // подпись, например "vs 1m"
  icon?: React.ReactNode;
  variant?: "primary" | "neutral" | "success" | "warning";
};

export function KpiTile({ label, value, sub, icon, variant = "neutral" }: KpiTileProps) {
  // Цвета для вариантов (темная тема)
  const getVariantClasses = (variant: string) => {
    switch (variant) {
      case "primary":
        return "bg-blue-500/10 border-blue-500/30 text-blue-400";
      case "success":
        return "bg-green-500/10 border-green-500/30 text-green-400";
      case "warning":
        return "bg-yellow-500/10 border-yellow-500/30 text-yellow-400";
      default:
        return "bg-slate-700/50 border-slate-600/50 text-slate-300";
    }
  };

  return (
    <div className={`p-4 rounded-lg border ${getVariantClasses(variant)}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium opacity-75">{label}</span>
        {icon && (
          <div className="text-lg opacity-60">
            {icon}
          </div>
        )}
      </div>
      
      <div className="text-2xl font-bold mb-1">{value}</div>
      
      {sub && (
        <div className="text-xs opacity-60">{sub}</div>
      )}
    </div>
  );
}
