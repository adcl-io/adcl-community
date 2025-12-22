/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React, { useState, useEffect } from 'react';
import { ThemeProvider } from 'next-themes';
import { ConversationHistoryProvider } from './contexts/ConversationHistoryContext';
import Navigation from './components/Navigation';
import PlaygroundPage from './pages/PlaygroundPage';
import HistoryPage from './pages/HistoryPage';
import ModelsPage from './pages/ModelsPage';
import MCPServersPage from './pages/MCPServersPage';
import TeamsPage from './pages/TeamsPage';
import AgentsPage from './pages/AgentsPage';
import RegistryPage from './pages/RegistryPage';
import WorkflowsPage from './pages/WorkflowsPage';
import TriggersPage from './pages/TriggersPage';
import { Toaster } from '@/components/ui/sonner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { AlertTriangle, Loader2, ServerCrash } from 'lucide-react';

// Error Boundary Component
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('React Error Boundary caught an error:', error, errorInfo);
    this.setState({ error, errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-background p-8 text-foreground">
          <div className="max-w-4xl mx-auto">
            <Alert className="bg-destructive/10 border-destructive">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              <AlertDescription className="text-destructive font-semibold text-lg">
                Something went wrong
              </AlertDescription>
            </Alert>

            <details className="mt-6 cursor-pointer">
              <summary className="text-blue-400 text-base hover:text-blue-300">
                Error Details
              </summary>
              <div className="mt-4 p-4 bg-muted rounded-md">
                <h3 className="font-semibold mb-2">Error:</h3>
                <pre className="text-red-400 whitespace-pre-wrap text-sm">
                  {this.state.error && this.state.error.toString()}
                </pre>
                {this.state.errorInfo && (
                  <>
                    <h3 className="font-semibold mt-4 mb-2">Component Stack:</h3>
                    <pre className="text-yellow-400 whitespace-pre-wrap text-xs">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  </>
                )}
              </div>
            </details>

            <Button
              onClick={() => window.location.reload()}
              className="mt-6"
            >
              Reload Page
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function App() {
  const [currentPage, setCurrentPage] = useState('playground');
  const [apiReady, setApiReady] = useState(false);
  const [apiError, setApiError] = useState(null);
  const [retryCount, setRetryCount] = useState(0);

  // Check API health on mount
  useEffect(() => {
    let isMounted = true;
    let retryTimeoutId;

    const checkApiHealth = async () => {
      try {
        // Create AbortController for timeout (better browser compatibility)
        const controller = new AbortController();
        const fetchTimeoutId = setTimeout(() => controller.abort(), 5000);

        const response = await fetch(`${API_URL}/health`, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
          signal: controller.signal
        });

        clearTimeout(fetchTimeoutId);

        if (response.ok && isMounted) {
          setApiReady(true);
          setApiError(null);
        } else if (isMounted) {
          throw new Error(`API health check failed: ${response.status}`);
        }
      } catch (error) {
        if (!isMounted) return;

        console.warn('API health check failed:', error.message);

        // Retry with exponential backoff (max 30 seconds)
        const delay = Math.min(2000 * Math.pow(1.5, retryCount), 30000);

        if (retryCount < 10) {
          setRetryCount(prev => prev + 1);
          retryTimeoutId = setTimeout(checkApiHealth, delay);
        } else {
          setApiError('Unable to connect to API server. Please check if the backend is running.');
        }
      }
    };

    checkApiHealth();

    return () => {
      isMounted = false;
      if (retryTimeoutId) clearTimeout(retryTimeoutId);
    };
  }, [retryCount]);

  // Show loading screen while API initializes
  if (!apiReady) {
    return (
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
        <div className="flex items-center justify-center min-h-screen bg-background">
          <div className="text-center space-y-6 p-8">
            {apiError ? (
              <>
                <ServerCrash className="h-16 w-16 mx-auto text-destructive animate-pulse" />
                <h2 className="text-2xl font-bold text-foreground">API Server Unavailable</h2>
                <p className="text-muted-foreground max-w-md">{apiError}</p>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">
                    The backend API server may still be starting up.
                  </p>
                  <Button
                    onClick={() => {
                      setApiError(null);
                      setRetryCount(0);
                    }}
                    variant="outline"
                  >
                    Retry Connection
                  </Button>
                </div>
              </>
            ) : (
              <>
                <Loader2 className="h-16 w-16 mx-auto text-primary animate-spin" />
                <h2 className="text-2xl font-bold text-foreground">Loading ADCL Platform</h2>
                <p className="text-muted-foreground">
                  Waiting for API server to initialize...
                  {retryCount > 0 && ` (attempt ${retryCount + 1})`}
                </p>
                <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                  <div className="w-2 h-2 bg-primary rounded-full animate-pulse" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-primary rounded-full animate-pulse" style={{ animationDelay: '200ms' }} />
                  <div className="w-2 h-2 bg-primary rounded-full animate-pulse" style={{ animationDelay: '400ms' }} />
                </div>
              </>
            )}
          </div>
        </div>
      </ThemeProvider>
    );
  }

  const renderPage = () => {
    switch (currentPage) {
      case 'playground':
        return <PlaygroundPage />;
      case 'history':
        return <HistoryPage onNavigate={setCurrentPage} />;
      case 'models':
        return <ModelsPage />;
      case 'mcps':
        return <MCPServersPage />;
      case 'teams':
        return <TeamsPage />;
      case 'agents':
        return <AgentsPage />;
      case 'registry':
        return <RegistryPage />;
      case 'workflows':
        return <WorkflowsPage />;
      case 'triggers':
        return <TriggersPage />;
      default:
        return <PlaygroundPage />;
    }
  };

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <ConversationHistoryProvider>
        <div className="flex min-h-screen bg-background">
          <Navigation currentPage={currentPage} onNavigate={setCurrentPage} />
          <main className="flex-1">
            {renderPage()}
          </main>
          <Toaster />
        </div>
      </ConversationHistoryProvider>
    </ThemeProvider>
  );
}

// Wrap App with ErrorBoundary
function AppWithErrorBoundary() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}

export default AppWithErrorBoundary;
