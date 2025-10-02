// Виджет предупреждений из последнего AI анализа
export type Alert = {
  id: string;
  type: "warning" | "error" | "info";
  message: string;
  severity: number; // 1-5
};

export type AlertsWidgetProps = {
  data?: Alert[];
};

export function AlertsWidget({ data }: AlertsWidgetProps) {
  // Читаем предупреждения из localStorage
  const getAlertsFromStorage = (): Alert[] => {
    try {
      const lastResult = localStorage.getItem('insights_last_result');
      if (!lastResult) return [];
      
      const result = JSON.parse(lastResult);
      const alerts: Alert[] = [];
      
      // Извлекаем риски как предупреждения
      if (result.key_risks && Array.isArray(result.key_risks)) {
        result.key_risks.forEach((risk: any, index: number) => {
          alerts.push({
            id: `risk-${index}`,
            type: risk.severity >= 4 ? "error" : "warning",
            message: risk.name || risk.why || "Risk identified",
            severity: risk.severity || 3
          });
        });
      }
      
      // Извлекаем предупреждения
      if (result.warnings && Array.isArray(result.warnings)) {
        result.warnings.forEach((warning: string, index: number) => {
          alerts.push({
            id: `warning-${index}`,
            type: "info",
            message: warning,
            severity: 2
          });
        });
      }
      
      return alerts.slice(0, 5); // Максимум 5 предупреждений
    } catch (error) {
      console.warn('Ошибка чтения предупреждений:', error);
      return [];
    }
  };

  const alerts = data && data.length > 0 ? data : getAlertsFromStorage();

  const getAlertIcon = (type: string) => {
    switch (type) {
      case "error": return "🚨";
      case "warning": return "⚠️";
      case "info": return "ℹ️";
      default: return "📢";
    }
  };

  const getAlertColor = (type: string) => {
    switch (type) {
      case "error": return "border-red-500/30 bg-red-500/10";
      case "warning": return "border-yellow-500/30 bg-yellow-500/10";
      case "info": return "border-blue-500/30 bg-blue-500/10";
      default: return "border-slate-600/30 bg-slate-700/30";
    }
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      <h3 className="text-lg font-semibold text-white mb-4">Alerts & Warnings</h3>
      
      {alerts.length === 0 ? (
        <div className="text-center py-8">
          <div className="text-slate-400 text-2xl mb-2">✅</div>
          <p className="text-slate-400">No alerts</p>
          <p className="text-sm text-slate-500">Run AI analysis to see warnings</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div key={alert.id} className={`p-3 rounded-lg border ${getAlertColor(alert.type)}`}>
              <div className="flex items-start space-x-3">
                <div className="text-lg">{getAlertIcon(alert.type)}</div>
                <div className="flex-1">
                  <div className="text-sm text-white">{alert.message}</div>
                  <div className="text-xs text-slate-400 mt-1">
                    Severity: {alert.severity}/5
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
