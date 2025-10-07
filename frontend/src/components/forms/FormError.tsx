import React from 'react';

export interface FormErrorProps {
  message: string;
  className?: string;
}

export const FormError: React.FC<FormErrorProps> = ({ message, className = '' }) => {
  if (!message) return null;

  return (
    <div
      className={`p-3 bg-red-900/20 border border-red-500/30 rounded-lg animate-in fade-in slide-in-from-top-2 duration-200 ${className}`}
      role="alert"
    >
      <p className="text-red-400 text-sm flex items-center">
        <svg
          className="w-4 h-4 mr-2 flex-shrink-0"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        {message}
      </p>
    </div>
  );
};
