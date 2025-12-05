/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React from 'react';

/**
 * Error Boundary Component
 * Catches React errors and displays fallback UI
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught error:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });

    // Optional: Log to error reporting service
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });

    // Optional: Call reset callback
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback({
          error: this.state.error,
          errorInfo: this.state.errorInfo,
          reset: this.handleReset,
        });
      }

      // Default fallback UI
      return (
        <div style={styles.container}>
          <h1 style={styles.title}>⚠️ Something went wrong</h1>
          <p style={styles.subtitle}>
            An error occurred in this component. Try refreshing the page.
          </p>

          <details style={styles.details}>
            <summary style={styles.summary}>Error Details</summary>
            <div style={styles.detailsContent}>
              <h3>Error:</h3>
              <pre style={styles.errorText}>
                {this.state.error && this.state.error.toString()}
              </pre>

              {this.state.errorInfo && (
                <>
                  <h3>Component Stack:</h3>
                  <pre style={styles.stackTrace}>
                    {this.state.errorInfo.componentStack}
                  </pre>
                </>
              )}
            </div>
          </details>

          <div style={styles.buttonGroup}>
            <button onClick={this.handleReset} style={styles.button}>
              Try Again
            </button>
            <button
              onClick={() => window.location.reload()}
              style={{...styles.button, ...styles.secondaryButton}}
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Styles
const styles = {
  container: {
    padding: '40px 20px',
    background: '#2d2d2d',
    color: '#fff',
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    color: '#ea4335',
    fontSize: '28px',
    marginBottom: '12px',
  },
  subtitle: {
    color: '#bbb',
    fontSize: '16px',
    marginBottom: '24px',
  },
  details: {
    marginTop: '20px',
    marginBottom: '24px',
    cursor: 'pointer',
    width: '100%',
    maxWidth: '800px',
  },
  summary: {
    color: '#8ab4f8',
    fontSize: '16px',
    padding: '10px',
    background: '#1e1e1e',
    borderRadius: '4px',
    userSelect: 'none',
  },
  detailsContent: {
    marginTop: '10px',
    padding: '16px',
    background: '#1e1e1e',
    borderRadius: '4px',
  },
  errorText: {
    color: '#ea4335',
    whiteSpace: 'pre-wrap',
    fontSize: '14px',
    overflow: 'auto',
  },
  stackTrace: {
    color: '#fbbc04',
    whiteSpace: 'pre-wrap',
    fontSize: '12px',
    overflow: 'auto',
  },
  buttonGroup: {
    display: 'flex',
    gap: '12px',
  },
  button: {
    padding: '12px 24px',
    background: '#8ab4f8',
    color: '#1e1e1e',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 'bold',
  },
  secondaryButton: {
    background: '#5f6368',
    color: '#fff',
  },
};

export default ErrorBoundary;
