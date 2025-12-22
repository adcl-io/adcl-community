/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';

// Mock the conversation history context
vi.mock('../contexts/ConversationHistoryContext', () => ({
  ConversationHistoryProvider: ({ children }) => <div>{children}</div>,
  useConversationHistoryContext: () => ({
    sessions: [],
    loadSessions: vi.fn(),
    loadSession: vi.fn()
  })
}));

// Mock all page components to avoid complex dependencies
vi.mock('../pages/PlaygroundPage', () => ({
  default: () => <div>PlaygroundPage</div>
}));
vi.mock('../pages/HistoryPage', () => ({
  default: () => <div>HistoryPage</div>
}));
vi.mock('../pages/ModelsPage', () => ({
  default: () => <div>ModelsPage</div>
}));
vi.mock('../pages/MCPServersPage', () => ({
  default: () => <div>MCPServersPage</div>
}));
vi.mock('../pages/TeamsPage', () => ({
  default: () => <div>TeamsPage</div>
}));
vi.mock('../pages/AgentsPage', () => ({
  default: () => <div>AgentsPage</div>
}));
vi.mock('../pages/RegistryPage', () => ({
  default: () => <div>RegistryPage</div>
}));
vi.mock('../pages/WorkflowsPage', () => ({
  default: () => <div>WorkflowsPage</div>
}));
vi.mock('../pages/TriggersPage', () => ({
  default: () => <div>TriggersPage</div>
}));
vi.mock('../components/Navigation', () => ({
  default: () => <div>Navigation</div>
}));

describe('App - API Health Check and Loading State', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('shows loading screen while waiting for API', async () => {
    // Mock fetch to fail (will show loading and retry)
    global.fetch = vi.fn(() => Promise.reject(new Error('Network error')));

    render(<App />);

    // Should show loading state
    expect(screen.getByText('Loading ADCL Platform')).toBeInTheDocument();
    expect(screen.getByText(/Waiting for API server to initialize/)).toBeInTheDocument();
  });

  it('shows app content when API health check succeeds', async () => {
    // Mock successful health check
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ status: 'healthy' })
      })
    );

    render(<App />);

    // Wait for health check to complete
    await waitFor(() => {
      expect(screen.queryByText('Loading ADCL Platform')).not.toBeInTheDocument();
    }, { timeout: 10000 });

    // Should show app content (Navigation and PlaygroundPage)
    expect(screen.getByText('Navigation')).toBeInTheDocument();
    expect(screen.getByText('PlaygroundPage')).toBeInTheDocument();
  });

  it('makes health check request to correct endpoint', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ status: 'healthy' })
      })
    );

    render(<App />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/health'),
        expect.objectContaining({
          method: 'GET',
          headers: { 'Content-Type': 'application/json' }
        })
      );
    });
  });

  it('handles non-ok responses as failures', async () => {
    // Mock fetch to return 500 error
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ error: 'Server error' })
      })
    );

    render(<App />);

    // Should show loading (will retry in background)
    expect(screen.getByText('Loading ADCL Platform')).toBeInTheDocument();
  });

  it('includes AbortController signal in fetch request', async () => {
    let capturedSignal;

    global.fetch = vi.fn((url, options) => {
      capturedSignal = options.signal;
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ status: 'healthy' })
      });
    });

    render(<App />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
    });

    // Signal should be present (AbortController)
    expect(capturedSignal).toBeDefined();
    expect(capturedSignal).toBeInstanceOf(AbortSignal);
  });

  it('cleans up on unmount', async () => {
    global.fetch = vi.fn(() => new Promise(() => {})); // Never resolves

    const { unmount } = render(<App />);

    // Verify component mounted
    expect(screen.getByText('Loading ADCL Platform')).toBeInTheDocument();

    // Unmount should not throw
    expect(() => unmount()).not.toThrow();
  });
});
