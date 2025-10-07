import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Modal, Button } from '../ui';
import { FormField, FormError } from '../forms';
import { Position } from '../../lib/api';

const editPositionSchema = z.object({
  symbol: z.string().min(1, 'Symbol is required'),
  quantity: z.string()
    .min(1, 'Quantity is required')
    .refine((val) => {
      const num = parseFloat(val);
      return !isNaN(num) && num > 0;
    }, 'Quantity must be greater than 0'),
  buy_price: z.string()
    .optional()
    .refine((val) => {
      if (!val || val === '') return true;
      const num = parseFloat(val);
      return !isNaN(num) && num >= 0;
    }, 'Buy price must be 0 or greater')
});

type EditPositionFormData = z.infer<typeof editPositionSchema>;

export interface EditPositionModalProps {
  isOpen: boolean;
  position: Position | null;
  isProcessing: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (data: { symbol: string; quantity: number; buy_price?: number }) => Promise<void>;
}

export const EditPositionModal: React.FC<EditPositionModalProps> = ({
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
  } = useForm<EditPositionFormData>({
    resolver: zodResolver(editPositionSchema),
    values: position
      ? {
          symbol: position.symbol,
          quantity: position.quantity.toString(),
          buy_price: position.buy_price?.toString() || ''
        }
      : undefined
  });

  const handleFormSubmit = async (data: EditPositionFormData) => {
    const submitData: { symbol: string; quantity: number; buy_price?: number } = {
      symbol: data.symbol.trim(),
      quantity: parseFloat(data.quantity)
    };

    if (data.buy_price && data.buy_price !== '') {
      submitData.buy_price = parseFloat(data.buy_price);
    }

    await onSubmit(submitData);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  if (!position) return null;

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Edit Position">
      <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
        <FormField
          {...register('symbol')}
          label="Symbol"
          placeholder="AAPL"
          error={errors.symbol}
          required
        />

        <FormField
          {...register('quantity')}
          label="Quantity"
          type="number"
          placeholder="10"
          min="0"
          step="0.01"
          error={errors.quantity}
          required
        />

        <FormField
          {...register('buy_price')}
          label="Buy Price"
          type="number"
          placeholder="150.00 (leave empty to use current market price)"
          min="0"
          step="0.01"
          error={errors.buy_price}
          helpText="If empty, will use current market price for P&L calculations"
        />

        {error && <FormError message={error} />}

        <div className="flex gap-3 pt-4">
          <Button
            type="submit"
            loading={isProcessing}
            fullWidth
          >
            Update Position
          </Button>
          <Button type="button" variant="secondary" onClick={handleClose} fullWidth>
            Cancel
          </Button>
        </div>
      </form>
    </Modal>
  );
};
