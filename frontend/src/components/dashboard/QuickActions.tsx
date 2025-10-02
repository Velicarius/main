// Быстрые действия для навигации по приложению
export function QuickActions() {
  const actions = [
    {
      label: "View Positions",
      description: "Manage your portfolio",
      href: "/positions",
      icon: "📊",
      color: "bg-blue-500/10 border-blue-500/30 hover:bg-blue-500/20"
    },
    {
      label: "Add Position",
      description: "Add new investment",
      href: "/positions?add=1",
      icon: "➕",
      color: "bg-green-500/10 border-green-500/30 hover:bg-green-500/20"
    },
    {
      label: "AI Insights",
      description: "Portfolio analysis",
      href: "/insights",
      icon: "🤖",
      color: "bg-purple-500/10 border-purple-500/30 hover:bg-purple-500/20"
    }
  ];

  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      <h3 className="text-lg font-semibold text-white mb-4">Quick Actions</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {actions.map((action) => (
          <button
            key={action.label}
            onClick={() => window.location.href = action.href}
            className={`p-4 rounded-lg border text-left transition-colors ${action.color}`}
          >
            <div className="flex items-center space-x-3">
              <div className="text-2xl">{action.icon}</div>
              <div>
                <div className="font-medium text-white">{action.label}</div>
                <div className="text-sm text-slate-300">{action.description}</div>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
