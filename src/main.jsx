import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './index.css';

class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null, showDetails: false };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('[ATLAS APP RUNTIME ERROR]', error, info);
  }

  handleRetry = () => {
    this.setState({ error: null });
    window.location.reload();
  };

  handleReset = () => {
    try {
      localStorage.removeItem('atlas-theme');
      localStorage.removeItem('atlas-sidebar-open');
      localStorage.removeItem('atlas-model');
      localStorage.removeItem('atlas-deep-research');
      sessionStorage.clear();
    } catch (e) {
      console.warn('Storage clear warning:', e);
    }
    window.location.href = '/atlas';
  };

  render() {
    if (this.state.error) {
      const errorMessage = typeof this.state.error?.message === 'string'
        ? this.state.error.message
        : String(this.state.error || 'Initialization error');

      return (
        <main className="grid min-h-screen place-items-center bg-[#131418] px-6 text-[#f2f3f5] font-sans">
          <section className="max-w-md text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xl font-bold">
              A
            </div>
            <p className="text-xl font-semibold text-[#f2f3f5]">Unable to load Atlas.</p>
            <p className="mt-2 text-sm text-[#8b8d96] leading-relaxed">
              The application encountered an unexpected runtime state. You can retry or start a completely fresh session.
            </p>

            <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
              <button
                type="button"
                className="rounded-xl bg-[#f15a3a] px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-[#e04a29] transition-colors cursor-pointer"
                onClick={this.handleRetry}
              >
                Retry
              </button>
              <button
                type="button"
                className="rounded-xl border border-[#303030] bg-[#1a1b20] px-4 py-2 text-sm font-medium text-[#c0c2cb] hover:border-[#f15a3a] hover:text-[#f2f3f5] transition-colors cursor-pointer"
                onClick={this.handleReset}
              >
                Start Clean Session
              </button>
            </div>

            <div className="mt-6 text-left">
              <button
                type="button"
                onClick={() => this.setState((prev) => ({ showDetails: !prev.showDetails }))}
                className="text-xs text-[#6e717b] hover:text-[#a0a3af] underline underline-offset-2 transition-colors mx-auto block"
              >
                {this.state.showDetails ? 'Hide error details' : 'View error details'}
              </button>
              {this.state.showDetails && (
                <div className="mt-3 max-h-48 overflow-y-auto rounded-lg bg-[#0c0d10] p-3 text-xs font-mono text-[#e57373] border border-[#2a2c35] break-words">
                  {errorMessage}
                </div>
              )}
            </div>
          </section>
        </main>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AppErrorBoundary>
      <App />
    </AppErrorBoundary>
  </React.StrictMode>
);
