/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import PlaygroundPage from '../PlaygroundPage';
import { mockSessions, mockMessages } from '../../test/mockData';
import axios from 'axios';

// Mock axios
vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn()
  }
}));

// Mock the conversation history context
vi.mock('../../contexts/ConversationHistoryContext', () => ({
  useConversationHistoryContext: () => ({
    currentSessionId: 'session-1',
    sessions: mockSessions,
    messages: mockMessages,
    loading: false,
    initialized: true,
    appendMessage: vi.fn(),
    loadSession: vi.fn(),
    startNewConversation: vi.fn(),
    loadSessions: vi.fn(),
    setMessages: vi.fn(),
    setCurrentSessionId: vi.fn()
  })
}));

describe('PlaygroundPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Mock axios for teams
    axios.get.mockResolvedValue({
      data: [
        {
          id: 'code-review-team',
          name: 'Code Review Team',
          description: 'Team for code review',
          agents: [
            { name: 'code-reviewer', role: 'Code Reviewer' },
            { name: 'research-assistant', role: 'Research Assistant' }
          ]
        }
      ]
    });

    // Mock fetch for token requests (PlaygroundPage uses fetch, not axios)
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          total_input_tokens: 100,
          total_output_tokens: 200,
          cumulative_input_tokens: 100,
          cumulative_output_tokens: 200,
          total_cost: 0.0123
        })
      })
    );
  });

  it('renders without history sidebar', () => {
    render(<PlaygroundPage />);
    
    // Should not have sidebar elements
    expect(screen.queryByText('Recent')).not.toBeInTheDocument();
  });

  it('displays team selector in header', () => {
    render(<PlaygroundPage />);
    
    expect(screen.getByText('Select Team')).toBeInTheDocument();
  });

  it('displays New Chat button in header', () => {
    render(<PlaygroundPage />);
    
    expect(screen.getByText('New Chat')).toBeInTheDocument();
  });

  it('displays team selector in header', async () => {
    render(<PlaygroundPage />);

    // Wait for teams to load asynchronously
    await waitFor(() => {
      expect(screen.getAllByText('Code Review Team').length).toBeGreaterThan(0);
    });
    expect(screen.getByText('(2 agents)')).toBeInTheDocument();
  });

  it('displays messages in chat area', () => {
    render(<PlaygroundPage />);
    
    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('Hi there!')).toBeInTheDocument();
  });

  it('does not show help text under input area', () => {
    render(<PlaygroundPage />);
    
    expect(screen.queryByText('Press Enter to send')).not.toBeInTheDocument();
  });
});
