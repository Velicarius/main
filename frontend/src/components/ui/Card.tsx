import React from 'react';

export type CardVariant = 'default' | 'gradient' | 'bordered';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
  header?: React.ReactNode;
  footer?: React.ReactNode;
  noPadding?: boolean;
}

const variantClasses: Record<CardVariant, string> = {
  default: 'bg-slate-800/50 backdrop-blur-xl border border-slate-700/50',
  gradient: 'bg-gradient-to-r from-slate-800/50 to-slate-700/50 backdrop-blur-xl border border-slate-600/50',
  bordered: 'bg-slate-800/50 backdrop-blur-xl border-2 border-slate-700/50'
};

export const Card: React.FC<CardProps> = ({
  variant = 'default',
  header,
  footer,
  noPadding = false,
  className = '',
  children,
  ...props
}) => {
  return (
    <div
      className={`rounded-xl shadow-lg ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {header && (
        <div className="p-6 border-b border-slate-700/50">
          {typeof header === 'string' ? (
            <h3 className="text-lg font-semibold text-white">{header}</h3>
          ) : (
            header
          )}
        </div>
      )}

      <div className={noPadding ? '' : 'p-6'}>
        {children}
      </div>

      {footer && (
        <div className="p-6 border-t border-slate-700/50">
          {footer}
        </div>
      )}
    </div>
  );
};
