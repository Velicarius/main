import React, { useState, useEffect } from 'react';

interface BalanceEditorProps {
  initialBalance: number;
  onBalanceUpdate: (newBalance: number) => Promise<void>;
}

export const BalanceEditor: React.FC<BalanceEditorProps> = ({
  initialBalance,
  onBalanceUpdate,
}) => {
  const [balance, setBalance] = useState(initialBalance);
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setBalance(initialBalance);
  }, [initialBalance]);

  const handleEdit = () => {
    setIsEditing(true);
    setError(null);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setBalance(initialBalance);
    setError(null);
  };

  const handleSave = async () => {
    if (balance < 0) {
      setError('Balance cannot be negative');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await onBalanceUpdate(balance);
      setIsEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update balance');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSave();
    } else if (e.key === 'Escape') {
      handleCancel();
    }
  };

  if (isEditing) {
    return (
      <div className="flex items-center space-x-2">
        <div className="relative">
          <input
            type="number"
            value={balance}
            onChange={(e) => setBalance(parseFloat(e.target.value) || 0)}
            onKeyDown={handleKeyDown}
            className="px-3 py-2 bg-slate-700/50 border rounded-lg text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 backdrop-blur-sm transition-all duration-200 border-slate-600/50 text-lg font-medium min-w-[120px]"
            placeholder="0.00"
            step="0.01"
            min="0"
            autoFocus
          />
          <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 text-sm font-medium">
            $
          </span>
        </div>
        
        <button
          onClick={handleSave}
          disabled={isLoading}
          className="px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
          ) : (
            'Save'
          )}
        </button>
        
        <button
          onClick={handleCancel}
          disabled={isLoading}
          className="px-3 py-2 bg-slate-600 hover:bg-slate-700 text-white rounded-lg font-medium transition-all duration-200 disabled:opacity-50"
        >
          Cancel
        </button>

        {error && (
          <div className="text-red-400 text-sm font-medium">
            {error}
          </div>
        )}
      </div>
    );
  }

  return (
    <div 
      className="flex items-center space-x-2 cursor-pointer group hover:bg-slate-700/30 rounded-lg px-3 py-2 transition-all duration-200"
      onClick={handleEdit}
    >
      <div className="text-lg font-bold text-green-400">
        ${balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
      </div>
      <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200">
        <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
        </svg>
      </div>
      <span className="text-xs text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
        Click to edit
      </span>
    </div>
  );
};







