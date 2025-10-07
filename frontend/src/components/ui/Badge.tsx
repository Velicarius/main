import React from 'react';

export type BadgeColor = 'green' | 'red' | 'blue' | 'yellow' | 'gray' | 'purple';
export type BadgeVariant = 'solid' | 'outline' | 'subtle';
export type BadgeSize = 'sm' | 'md' | 'lg';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  color?: BadgeColor;
  variant?: BadgeVariant;
  size?: BadgeSize;
  icon?: React.ReactNode;
}

const colorClasses: Record<BadgeColor, Record<BadgeVariant, string>> = {
  green: {
    solid: 'bg-green-500 text-white',
    outline: 'border-2 border-green-500 text-green-400 bg-transparent',
    subtle: 'bg-green-500/20 text-green-400 border border-green-500/30'
  },
  red: {
    solid: 'bg-red-500 text-white',
    outline: 'border-2 border-red-500 text-red-400 bg-transparent',
    subtle: 'bg-red-500/20 text-red-400 border border-red-500/30'
  },
  blue: {
    solid: 'bg-blue-500 text-white',
    outline: 'border-2 border-blue-500 text-blue-400 bg-transparent',
    subtle: 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
  },
  yellow: {
    solid: 'bg-yellow-500 text-white',
    outline: 'border-2 border-yellow-500 text-yellow-400 bg-transparent',
    subtle: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
  },
  gray: {
    solid: 'bg-slate-500 text-white',
    outline: 'border-2 border-slate-500 text-slate-400 bg-transparent',
    subtle: 'bg-slate-500/20 text-slate-400 border border-slate-500/30'
  },
  purple: {
    solid: 'bg-purple-500 text-white',
    outline: 'border-2 border-purple-500 text-purple-400 bg-transparent',
    subtle: 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
  }
};

const sizeClasses: Record<BadgeSize, string> = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
  lg: 'px-3 py-1.5 text-base'
};

export const Badge: React.FC<BadgeProps> = ({
  color = 'gray',
  variant = 'subtle',
  size = 'md',
  icon,
  className = '',
  children,
  ...props
}) => {
  return (
    <span
      className={`
        inline-flex items-center font-medium rounded-full
        ${colorClasses[color][variant]}
        ${sizeClasses[size]}
        ${className}
      `}
      {...props}
    >
      {icon && <span className="mr-1">{icon}</span>}
      {children}
    </span>
  );
};
