/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React, { useState } from 'react';
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
import { AlertTriangle } from 'lucide-react';

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

function App() {
  const [currentPage, setCurrentPage] = useState('playground');

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
