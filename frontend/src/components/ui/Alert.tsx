import React from 'react';

export type AlertType = 'success' | 'error' | 'warning' | 'info';

export interface AlertProps {
  type?: AlertType;
  title?: string;
  message: string;
  dismissible?: boolean;
  onDismiss?: () => void;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

const typeConfig: Record<AlertType, { bgClass: string; borderClass: string; textClass: string; icon: JSX.Element }> = {
  success: {
    bgClass: 'bg-gradient-to-r from-green-900/20 to-green-800/20',
    borderClass: 'border-green-500/30',
    textClass: 'text-green-400',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    )
  },
  error: {
    bgClass: 'bg-gradient-to-r from-red-900/20 to-red-800/20',
    borderClass: 'border-red-500/30',
    textClass: 'text-red-400',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    )
  },
  warning: {
    bgClass: 'bg-gradient-to-r from-yellow-900/20 to-yellow-800/20',
    borderClass: 'border-yellow-500/30',
    textClass: 'text-yellow-400',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    )
  },
  info: {
    bgClass: 'bg-gradient-to-r from-blue-900/20 to-blue-800/20',
    borderClass: 'border-blue-500/30',
    textClass: 'text-blue-400',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    )
  }
};

export const Alert: React.FC<AlertProps> = ({
  type = 'info',
  title,
  message,
  dismissible = false,
  onDismiss,
  action,
  className = ''
}) => {
  const config = typeConfig[type];

  return (
    <div
      className={`${config.bgClass} border ${config.borderClass} rounded-xl p-6 backdrop-blur-sm ${className}`}
      role="alert"
    >
      <div className="flex items-start space-x-3">
        <div className={`flex-shrink-0 w-6 h-6 ${config.bgClass} rounded-full flex items-center justify-center ${config.textClass}`}>
          {config.icon}
        </div>

        <div className="flex-1 min-w-0">
          {title && (
            <h4 className={`${config.textClass} font-semibold mb-1`}>
              {title}
            </h4>
          )}
          <p className={`${config.textClass} ${title ? '' : 'font-medium'}`}>
            {message}
          </p>

          {action && (
            <button
              onClick={action.onClick}
              className={`mt-3 text-sm ${config.textClass} underline hover:no-underline transition-all`}
            >
              {action.label}
            </button>
          )}
        </div>

        {dismissible && onDismiss && (
          <button
            onClick={onDismiss}
            className={`flex-shrink-0 ${config.textClass} hover:text-white transition-colors`}
            aria-label="Dismiss alert"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
};
