import { useState } from 'react';
import { Position, updatePosition, deletePosition, sellPosition, SellPositionRequest, AddPositionRequest } from '../lib/api';

export interface UsePositionActionsReturn {
  // Edit modal state
  editingPosition: Position | null;
  isProcessingEdit: boolean;
  editError: string | null;
  openEditModal: (position: Position) => void;
  closeEditModal: () => void;
  handleEdit: (data: Partial<AddPositionRequest>) => Promise<void>;

  // Sell modal state
  sellingPosition: Position | null;
  isProcessingSell: boolean;
  sellError: string | null;
  openSellModal: (position: Position) => void;
  closeSellModal: () => void;
  handleSell: (data: { quantity: number; sell_price?: number }) => Promise<void>;

  // Delete action
  handleDelete: (id: string) => Promise<void>;
}

export interface UsePositionActionsOptions {
  onSuccess?: () => void;
}

export const usePositionActions = (
  options?: UsePositionActionsOptions
): UsePositionActionsReturn => {
  const { onSuccess } = options || {};

  // Edit modal state
  const [editingPosition, setEditingPosition] = useState<Position | null>(null);
  const [isProcessingEdit, setIsProcessingEdit] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // Sell modal state
  const [sellingPosition, setSellingPosition] = useState<Position | null>(null);
  const [isProcessingSell, setIsProcessingSell] = useState(false);
  const [sellError, setSellError] = useState<string | null>(null);

  // Edit actions
  const openEditModal = (position: Position) => {
    setEditingPosition(position);
    setEditError(null);
  };

  const closeEditModal = () => {
    setEditingPosition(null);
    setEditError(null);
  };

  const handleEdit = async (data: Partial<AddPositionRequest>) => {
    if (!editingPosition) return;

    try {
      setIsProcessingEdit(true);
      setEditError(null);

      await updatePosition(editingPosition.id, data);

      closeEditModal();
      if (onSuccess) onSuccess();
    } catch (err) {
      setEditError(err instanceof Error ? err.message : 'Failed to update position');
    } finally {
      setIsProcessingEdit(false);
    }
  };

  // Sell actions
  const openSellModal = (position: Position) => {
    setSellingPosition(position);
    setSellError(null);
  };

  const closeSellModal = () => {
    setSellingPosition(null);
    setSellError(null);
  };

  const handleSell = async (data: { quantity: number; sell_price?: number }) => {
    if (!sellingPosition) return;

    try {
      setIsProcessingSell(true);
      setSellError(null);

      const sellData: SellPositionRequest = {
        position_id: sellingPosition.id,
        quantity: data.quantity,
        sell_price: data.sell_price
      };

      await sellPosition(sellData);

      closeSellModal();
      if (onSuccess) onSuccess();
    } catch (err) {
      setSellError(err instanceof Error ? err.message : 'Failed to sell position');
    } finally {
      setIsProcessingSell(false);
    }
  };

  // Delete action
  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this position?')) {
      return;
    }

    try {
      await deletePosition(id);
      if (onSuccess) onSuccess();
    } catch (err) {
      // Could add error toast here
      console.error('Failed to delete position:', err);
    }
  };

  return {
    editingPosition,
    isProcessingEdit,
    editError,
    openEditModal,
    closeEditModal,
    handleEdit,

    sellingPosition,
    isProcessingSell,
    sellError,
    openSellModal,
    closeSellModal,
    handleSell,

    handleDelete
  };
};
