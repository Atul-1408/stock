import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

/** Catches render errors so one broken widget doesn't blank the whole app. */
export default class ErrorBoundary extends React.Component {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error("UI crash:", error, info?.componentStack);
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div
        role="alert"
        className="p-6 m-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-center font-mono space-y-3"
      >
        <div className="flex justify-center text-rose-400">
          <AlertTriangle size={32} />
        </div>
        <h2 className="text-sm font-bold text-white uppercase tracking-wider">Widget Interrupted</h2>
        <p className="text-xs text-slate-300">
          This component hit an unexpected error. Your portfolio and data are safe.
        </p>
        <button
          onClick={() => this.setState({ hasError: false })}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30 text-xs font-bold focus-visible:ring-2 focus-visible:ring-rose-500 focus-visible:outline-none transition-colors"
        >
          <RefreshCw size={12} />
          <span>Retry Component</span>
        </button>
      </div>
    );
  }
}

