/**
 * TradingPlaceholder — legacy entry point preserved for compatibility.
 * Phase 5 now renders the real trading workspace.
 */
import TradingWorkspace from '../trading/TradingWorkspace.jsx';

export default function TradingPlaceholder() {
  return <TradingWorkspace />;
}
