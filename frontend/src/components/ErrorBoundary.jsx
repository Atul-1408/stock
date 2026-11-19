import React from "react";

/** Catches render errors so one broken widget doesn't blank the whole app. */
export default class ErrorBoundary extends React.Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error("UI crash:", error, info?.componentStack);
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div role="alert" style={{ padding: "2rem", textAlign: "center" }}>
        <h2>Something went wrong</h2>
        <p>The page hit an unexpected error. Your data is safe.</p>
        <button onClick={() => window.location.reload()}>Reload page</button>
      </div>
    );
  }
}
