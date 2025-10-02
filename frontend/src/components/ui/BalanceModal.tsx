import React, { useState, useEffect } from 'react';
import { Modal } from './Modal';

interface BalanceModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentBalance: number;
  onBalanceUpdate: (newBalance: number) => Promise<void>;
}

export const BalanceModal: React.FC<BalanceModalProps> = ({
  isOpen,
  onClose,
  currentBalance,
  onBalanceUpdate,
}) => {
  const [tempBalance, setTempBalance] = useState(currentBalance);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Устанавливаем текущий баланс при открытии
  useEffect(() => {
    if (isOpen) {
      setTempBalance(currentBalance);
      setInputValue(currentBalance.toString());
      setError(null);
    }
  }, [isOpen, currentBalance]);

  const handleSubmit = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      await onBalanceUpdate(tempBalance);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update balance');
    } finally {
      setIsLoading(false);
    }
  };

  const handleBalanceChange = (value: string) => {
    // Убираем все нечисловые символы кроме точки
    let cleanValue = value.replace(/[^\d.]/g, '');
    
    // Предотвращаем множественные точки
    const dotCount = (cleanValue.match(/\./g) || []).length;
    if (dotCount > 1) {
      // Оставляем только первую точку
      const firstDotIndex = cleanValue.indexOf('.');
      cleanValue = cleanValue.slice(0, firstDotIndex + 1) + cleanValue.slice(firstDotIndex + 1).replace(/\./g, '');
    }
    
    // Убираем ведущие нули, но сохраняем "0." для дробных чисел
    if (cleanValue.startsWith('0') && cleanValue.length > 1 && cleanValue[1] !== '.') {
      cleanValue = cleanValue.replace(/^0+/, '');
    }
    
    // Обновляем inputValue для отображения
    setInputValue(cleanValue);
    
    // Обновляем tempBalance только для валидных чисел
    if (cleanValue === '') {
      setTempBalance(0);
    } else if (cleanValue === '.') {
      // Разрешаем точку - пользователь в процессе ввода дробного числа
      setTempBalance(0);
    } else {
      const numValue = parseFloat(cleanValue);
      if (!isNaN(numValue)) {
        setTempBalance(numValue);
      }
    }
  };

  const difference = tempBalance - currentBalance;
  const isDeposit = difference > 0;
  const isWithdrawal = difference < 0;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Manage Free USD"
      className="max-h-[90vh] overflow-y-auto"
    >
      <div className="space-y-6">
        {/* Slider */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-3">
            Adjust Balance
          </label>
          <input
            type="range"
            min="0"
            max="100000"
            step="0.01"
            value={tempBalance}
            onChange={(e) => {
              const newValue = parseFloat(e.target.value);
              setTempBalance(newValue);
              setInputValue(newValue.toString());
            }}
            className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-xs text-slate-400 mt-2">
            <span>$0</span>
            <span>$100,000</span>
          </div>
        </div>

        {/* Exact Amount Input */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Exact Amount (USD)
          </label>
          <input
            type="text"
            inputMode="decimal"
            value={inputValue}
            onChange={(e) => handleBalanceChange(e.target.value)}
            className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white text-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="0.00"
          />
        </div>

        {/* Transaction Preview */}
        {difference !== 0 && (
          <div className="bg-slate-700/50 rounded-lg p-4">
            <div className="text-center">
              <p className="text-sm text-slate-400 mb-2">Transaction Preview</p>
              <p className={`text-3xl font-bold mb-2 ${
                isDeposit ? 'text-green-400' : isWithdrawal ? 'text-red-400' : 'text-slate-300'
              }`}>
                {isDeposit ? '+' : ''}${Math.abs(difference).toFixed(2)}
              </p>
              <p className="text-sm text-slate-400 mb-1">
                {isDeposit ? 'Deposit to account' : isWithdrawal ? 'Withdrawal from account' : 'No change'}
              </p>
              <p className="text-lg text-slate-200">
                New balance: ${tempBalance.toFixed(2)}
              </p>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="bg-red-500/20 border border-red-500/30 rounded-lg p-3">
            <div className="text-red-400 text-sm font-medium">
              {error}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-3 pt-4">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isLoading || difference === 0}
            className="flex-1 px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-500 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center justify-center"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            ) : (
              'Update Balance'
            )}
          </button>
        </div>
      </div>
    </Modal>
  );
};
