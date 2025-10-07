import React from 'react';

export type SpinnerSize = 'sm' | 'md' | 'lg';
export type SpinnerColor = 'blue' | 'white' | 'green' | 'red';

export interface SpinnerProps {
  size?: SpinnerSize;
  color?: SpinnerColor;
  label?: string;
  className?: string;
}

const sizeClasses: Record<SpinnerSize, string> = {
  sm: 'w-4 h-4 border-2',
  md: 'w-8 h-8 border-4',
  lg: 'w-12 h-12 border-4'
};

const colorClasses: Record<SpinnerColor, string> = {
  blue: 'border-blue-500/30 border-t-blue-500',
  white: 'border-white/30 border-t-white',
  green: 'border-green-500/30 border-t-green-500',
  red: 'border-red-500/30 border-t-red-500'
};

export const Spinner: React.FC<SpinnerProps> = ({
  size = 'md',
  color = 'blue',
  label,
  className = ''
}) => {
  return (
    <div className={`flex flex-col items-center justify-center space-y-4 ${className}`}>
      <div
        className={`${sizeClasses[size]} ${colorClasses[color]} rounded-full animate-spin`}
        role="status"
        aria-label={label || 'Loading'}
      />
      {label && (
        <div className="text-slate-400 text-sm">{label}</div>
      )}
    </div>
  );
};
