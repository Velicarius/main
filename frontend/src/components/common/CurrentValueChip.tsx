import { fmtCurrency } from '../../lib/format';

export function CurrentValueChip({ value, currency }: { value: number; currency: 'USD' | 'EUR' | 'PLN' }) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full bg-zinc-800/70 px-3 py-1.5 text-sm border border-zinc-700">
      <span className="opacity-70">Current</span>
      <span className="font-semibold">{fmtCurrency(value, currency)}</span>
    </div>
  );
}
