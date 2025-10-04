import { AssetAllocation } from '../../types/strategy';

interface AssetAllocationChartProps {
  allocation: AssetAllocation;
}

export function AssetAllocationChart({ allocation }: AssetAllocationChartProps) {
  const { equities = 0, bonds = 0, cash = 0, alternatives = 0 } = allocation;
  
  // Calculate total to ensure percentages are normalized
  const total = equities + bonds + cash + alternatives;
  const normalizedData = [
    { name: 'Equities', value: Math.round(equities), color: '#60a5fa' },
    { name: 'Bonds', value: Math.round(bonds), color: '#34d399' },
    { name: 'Cash', value: Math.round(cash), color: '#fbbf24' },
    ...(alternatives > 0 ? [{ name: 'Alternatives', value: Math.round(alternatives), color: '#a78bfa' }] : [])
  ];

  return (
    <div className="space-y-4">
      {/* Simple Bar Chart */}
      <div className="space-y-2">
        {normalizedData.map((item) => (
          <div key={item.name} className="flex items-center justify-between space-x-3">
            <div className="flex items-center space-x-2">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: item.color }}
              />
              <span className="text-sm text-slate-300">{item.name}</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-16 bg-slate-600/50 rounded-full h-2">
                <div 
                  className="h-2 rounded-full transition-all duration-500"
                  style={{ 
                    width: `${item.value}%`,
                    backgroundColor: item.color 
                  }}
                />
              </div>
              <span className="text-sm text-white font-medium min-w-[3rem] text-right">
                {item.value}%
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="pt-2 border-t border-slate-600/50">
        <div className="flex justify-between text-xs text-slate-400">
          <span>Total Allocation:</span>
          <span className="text-white font-medium">{total}%</span>
        </div>
      </div>
    </div>
  );
}

