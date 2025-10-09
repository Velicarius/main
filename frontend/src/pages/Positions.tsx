import { useState, useEffect, useMemo } from 'react';
import { getPositions, addPosition, getBalance, getCashLedger, CashLedgerMetric, AddPositionRequest, Position } from '../lib/api';
import { useAuthStore } from '../store/auth';
import { AddPositionForm } from '../components/common/AddPositionForm';
import { PortfolioDisplay } from '../components/common/PortfolioDisplay';
import { PositionsTable, PositionsSummaryStats, EditPositionModal, SellPositionModal, LocalTotals } from '../components/positions';
import { usePositionsTable } from '../hooks/usePositionsTable';
import { usePositionActions } from '../hooks/usePositionActions';
import { Spinner, Alert, SegmentedControl } from '../components/ui';

export default function Positions() {
  const { loggedIn } = useAuthStore();
  const [positions, setPositions] = useState<Position[]>([]);
  const [cashLedgerMetrics, setCashLedgerMetrics] = useState<CashLedgerMetric | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedPositionId, setExpandedPositionId] = useState<string | null>(null);
  const [isAddingPosition, setIsAddingPosition] = useState(false);
  
  // Asset class tab state with localStorage persistence
  const [activeAssetClass, setActiveAssetClass] = useState<'EQUITY' | 'CRYPTO'>(() => {
    const saved = localStorage.getItem('positions-active-asset-class');
    return (saved as 'EQUITY' | 'CRYPTO') || 'EQUITY';
  });
  
  // Update localStorage when tab changes
  useEffect(() => {
    localStorage.setItem('positions-active-asset-class', activeAssetClass);
  }, [activeAssetClass]);

  // Fetch positions data
  const fetchPositions = async () => {
    try {
      setLoading(true);
      setError(null);

      const pos = await getPositions();

      // Filter out USD positions and map last_price to last for compatibility
      const nonUsdPositions = pos
        .filter(p => p.symbol !== 'USD')
        .map(p => ({
          ...p,
          last: p.last_price  // Map API's last_price to last for component compatibility
        }));
      setPositions(nonUsdPositions);

      // Load cash ledger metrics
      try {
        const cashLedger = await getCashLedger();
        setCashLedgerMetrics(cashLedger);
      } catch (cashLedgerError) {
        console.warn('Failed to fetch cash ledger:', cashLedgerError);
        // Fallback to old logic
        try {
          const balanceResponse = await getBalance();
          setCashLedgerMetrics({
            free_usd: balanceResponse.usd_balance,
            portfolio_balance: 0,
            total_equity: balanceResponse.usd_balance,
            positions_count: 0
          });
        } catch (balanceError) {
          const usdPosition = pos.find(p => p.symbol === 'USD');
          const fallbackBalance = usdPosition ? Number(usdPosition.quantity) : 0;
          setCashLedgerMetrics({
            free_usd: fallbackBalance,
            portfolio_balance: 0,
            total_equity: fallbackBalance,
            positions_count: 0
          });
        }
      }
    } catch (err) {
      console.error('Error fetching positions:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch positions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPositions();
  }, []);

  useEffect(() => {
    if (loggedIn) {
      fetchPositions();
    }
  }, [loggedIn]);

  // Filter positions by active asset class
  const filteredPositions = useMemo(() => {
    return positions.filter(position => position.asset_class === activeAssetClass);
  }, [positions, activeAssetClass]);

  // Use custom hooks for table sorting and actions with filtered positions
  const { sortField, sortDirection, sortedPositions, handleSort } = usePositionsTable(filteredPositions);

  const {
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
  } = usePositionActions({ onSuccess: fetchPositions });

  // Add position handler - use active tab's asset class
  const handleAddPosition = async (data: { symbol: string; quantity: number; asset_class?: 'EQUITY' | 'CRYPTO' }) => {
    try {
      setIsAddingPosition(true);

      const newPosition: AddPositionRequest = {
        symbol: data.symbol.toUpperCase(),
        quantity: data.quantity,
        asset_class: data.asset_class || activeAssetClass, // Use active tab's asset class
      };

      await addPosition(newPosition);
      await fetchPositions();
    } catch (err) {
      console.error('Failed to add position:', err);
      throw err;
    } finally {
      setIsAddingPosition(false);
    }
  };

  // Toggle expanded row
  const handleToggleExpand = (id: string) => {
    setExpandedPositionId(expandedPositionId === id ? null : id);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="md" label="Loading positions..." />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
            📊 Positions
          </h1>
          <p className="text-slate-400 mt-2">Manage your investment positions</p>
        </div>
        <div className="hidden sm:flex items-center space-x-2 text-sm text-slate-400">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          <span>Live prices</span>
        </div>
      </div>

      {/* Cash Ledger Display */}
      {cashLedgerMetrics && (
        <PortfolioDisplay
          metrics={cashLedgerMetrics}
          onMetricsUpdate={() => fetchPositions()}
        />
      )}

      {/* Add Position Form */}
      <AddPositionForm onSubmit={handleAddPosition} isLoading={isAddingPosition} />

      {/* Error Display */}
      {error && (
        <Alert type="error" message={error} />
      )}

      {/* Asset Class Tabs */}
      <div className="flex items-center justify-between">
        <SegmentedControl
          options={[
            { value: 'EQUITY', label: 'Stocks', icon: '📈' },
            { value: 'CRYPTO', label: 'Crypto', icon: '₿' }
          ]}
          value={activeAssetClass}
          onChange={(value) => setActiveAssetClass(value as 'EQUITY' | 'CRYPTO')}
        />
        <div className="text-sm text-slate-400">
          {filteredPositions.length} {filteredPositions.length === 1 ? 'position' : 'positions'}
        </div>
      </div>

      {/* Local Totals for Current Asset Class */}
      {positions.length > 0 && (
        <LocalTotals positions={positions} assetClass={activeAssetClass} />
      )}

      {/* Summary Stats - Global Portfolio (unchanged) */}
      {positions.length > 0 && (
        <PositionsSummaryStats positions={positions} />
      )}

      {/* Positions Table */}
      <PositionsTable
        positions={sortedPositions}
        sortField={sortField}
        sortDirection={sortDirection}
        expandedPositionId={expandedPositionId}
        onSort={handleSort}
        onToggleExpand={handleToggleExpand}
        onSell={openSellModal}
        onEdit={openEditModal}
        onDelete={handleDelete}
      />

      {/* Edit Position Modal */}
      <EditPositionModal
        isOpen={!!editingPosition}
        position={editingPosition}
        isProcessing={isProcessingEdit}
        error={editError}
        onClose={closeEditModal}
        onSubmit={handleEdit}
      />

      {/* Sell Position Modal */}
      <SellPositionModal
        isOpen={!!sellingPosition}
        position={sellingPosition}
        isProcessing={isProcessingSell}
        error={sellError}
        onClose={closeSellModal}
        onSubmit={handleSell}
      />
    </div>
  );
}
