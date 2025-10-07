import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Modal, Button } from '../ui';
import { FormField, FormError } from '../forms';
import { Position } from '../../lib/api';

const sellPositionSchema = z.object({
  quantity: z.string()
    .min(1, 'Quantity is required')
    .refine((val) => {
      const num = parseFloat(val);
      return !isNaN(num) && num > 0;
    }, 'Quantity must be greater than 0'),
  sell_price: z.string()
    .optional()
    .refine((val) => {
      if (!val || val === '') return true;
      const num = parseFloat(val);
      return !isNaN(num) && num >= 0;
    }, 'Sell price must be 0 or greater')
});

type SellPositionFormData = z.infer<typeof sellPositionSchema>;

export interface SellPositionModalProps {
  isOpen: boolean;
  position: Position | null;
  isProcessing: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (data: { quantity: number; sell_price?: number }) => Promise<void>;
}

export const SellPositionModal: React.FC<SellPositionModalProps> = ({
  isOpen,
  position,
  isProcessing,
  error,
  onClose,
  onSubmit
}) => {
  const {
    register,
    handleSubmit,
    formState: { errors },
    reset
  } = useForm<SellPositionFormData>({
    resolver: zodResolver(sellPositionSchema),
    defaultValues: {
      quantity: '',
      sell_price: position?.buy_price?.toString() || ''
    }
  });

  const availableQuantity = position?.quantity || 0;

  // Custom validation for quantity not exceeding available
  const validateQuantity = (value: string) => {
    const num = parseFloat(value);
    if (isNaN(num)) return 'Invalid quantity';
    if (num > availableQuantity) {
      return `Cannot sell more than ${availableQuantity} shares`;
    }
    return true;
  };

  const handleFormSubmit = async (data: SellPositionFormData) => {
    const submitData: { quantity: number; sell_price?: number } = {
      quantity: parseFloat(data.quantity)
    };

    if (data.sell_price && data.sell_price !== '') {
      submitData.sell_price = parseFloat(data.sell_price);
    }

    await onSubmit(submitData);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  if (!position) return null;

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Sell Position">
      <div className="mb-6 p-4 bg-slate-700/30 rounded-lg">
        <div className="text-sm text-slate-400 mb-1">Selling</div>
        <div className="text-white font-medium text-lg">{position.symbol}</div>
        <div className="text-sm text-slate-400 mt-1">
          Available: {availableQuantity.toLocaleString()} shares
        </div>
      </div>

      <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
        <FormField
          {...register('quantity', { validate: validateQuantity })}
          label="Quantity to Sell"
          type="number"
          placeholder="0"
          min="0"
          max={availableQuantity}
          step="0.01"
          error={errors.quantity}
          required
        />

        <FormField
          {...register('sell_price')}
          label="Sell Price (optional)"
          type="number"
          placeholder="0.00"
          min="0"
          step="0.01"
          error={errors.sell_price}
          helpText={`If empty, will use buy price: $${position.buy_price?.toFixed(2) || '0.00'}`}
        />

        {error && <FormError message={error} />}

        <div className="flex gap-3 pt-4">
          <Button
            type="submit"
            variant="success"
            loading={isProcessing}
            fullWidth
          >
            Sell Position
          </Button>
          <Button type="button" variant="secondary" onClick={handleClose} fullWidth>
            Cancel
          </Button>
        </div>
      </form>
    </Modal>
  );
};
