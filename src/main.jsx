import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './index.css';

class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('[ATLAS APP RUNTIME ERROR]', error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <main className="grid min-h-screen place-items-center bg-[#131418] px-6 text-[#f2f3f5]">
          <section className="max-w-md text-center">
            <p className="text-lg font-semibold">Unable to load Atlas.</p>
            <p className="mt-2 text-sm text-[#8b8d96]">The application hit an initialization error. Retry to start a clean session.</p>
            <button className="mt-5 rounded-lg border border-[#303030] px-4 py-2 text-sm hover:border-[#f15a3a]" onClick={() => window.location.reload()}>
              Retry
            </button>
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
