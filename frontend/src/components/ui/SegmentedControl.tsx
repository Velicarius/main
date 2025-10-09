import React from 'react';

interface SegmentedControlProps {
  options: Array<{
    value: string;
    label: string;
    icon?: string;
  }>;
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

export const SegmentedControl: React.FC<SegmentedControlProps> = ({
  options,
  value,
  onChange,
  className = ''
}) => {
  return (
    <div className={`inline-flex bg-slate-700/50 rounded-lg p-1 border border-slate-600/50 ${className}`}>
      {options.map((option) => (
        <button
          key={option.value}
          onClick={() => onChange(option.value)}
          className={`
            relative px-4 py-2 text-sm font-medium rounded-md transition-all duration-200
            flex items-center gap-2 min-w-[80px] justify-center
            ${
              value === option.value
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-300 hover:text-white hover:bg-slate-600/50'
            }
          `}
        >
          {option.icon && <span>{option.icon}</span>}
          <span>{option.label}</span>
        </button>
      ))}
    </div>
  );
};

