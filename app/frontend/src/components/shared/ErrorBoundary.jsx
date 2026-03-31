/**
 * ErrorBoundary — React class-based error boundary.
 * Catches render-time errors in the subtree and shows a recovery UI.
 * Never swallows errors — always logs to console.error.
 *
 * Usage:
 *   <ErrorBoundary label="Trading Workspace">
 *     <TradingWorkspace />
 *   </ErrorBoundary>
 */
import { Component } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    // Explicit error logging — never silent
    console.error('[ErrorBoundary] Caught render error:', error, info.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    const label = this.props.label ?? 'Component';

    return (
      <div className="flex flex-col items-center justify-center min-h-[200px] gap-4 rounded-2xl border border-red-500/20 bg-[#1a0d0d] p-8 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-red-500/10 text-red-400">
          <AlertTriangle size={22} />
        </div>
        <div>
          <p className="text-sm font-bold text-red-300">{label} encountered an error</p>
          <p className="mt-1 text-xs text-gray-500 max-w-xs">
            {this.state.error?.message ?? 'An unexpected error occurred. The component could not render.'}
          </p>
        </div>
        <button
          type="button"
          onClick={this.handleReset}
          className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-2 text-xs font-semibold text-red-300 transition hover:bg-red-500/20"
        >
          <RefreshCw size={13} />
          Try again
        </button>
      </div>
    );
  }
}
