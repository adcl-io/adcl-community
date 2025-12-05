/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import HistoryPage from '../HistoryPage';
import { mockSessions } from '../../test/mockData';

// Mock the conversation history context
vi.mock('../../contexts/ConversationHistoryContext', () => ({
  useConversationHistoryContext: () => ({
    sessions: mockSessions,
    loadSessions: vi.fn(),
    loadSession: vi.fn(),
    searchMessages: vi.fn().mockResolvedValue([])
  })
}));

describe('HistoryPage', () => {
  const mockOnNavigate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders history page with title and description', () => {
    render(<HistoryPage onNavigate={mockOnNavigate} />);
    
    expect(screen.getByText('Conversation History')).toBeInTheDocument();
    expect(screen.getByText('View and manage all your conversations')).toBeInTheDocument();
  });

  it('displays list of conversations when sessions exist', () => {
    render(<HistoryPage onNavigate={mockOnNavigate} />);
    
    expect(screen.getByText('Test Conversation 1')).toBeInTheDocument();
    expect(screen.getByText('Test Conversation 2')).toBeInTheDocument();
    expect(screen.getByText('Security Scan Discussion')).toBeInTheDocument();
  });

  it('displays correct message count for each session', () => {
    render(<HistoryPage onNavigate={mockOnNavigate} />);
    
    expect(screen.getByText('5 messages')).toBeInTheDocument();
    expect(screen.getByText('3 messages')).toBeInTheDocument();
    expect(screen.getByText('10 messages')).toBeInTheDocument();
  });

  it('filters conversations based on search input', async () => {
    render(<HistoryPage onNavigate={mockOnNavigate} />);
    
    const searchInput = screen.getByPlaceholderText('Search conversations...');
    fireEvent.change(searchInput, { target: { value: 'Security' } });
    
    await waitFor(() => {
      expect(screen.getByText('Security Scan Discussion')).toBeInTheDocument();
      expect(screen.queryByText('Test Conversation 1')).not.toBeInTheDocument();
    });
  });

  it('shows total conversation count', () => {
    render(<HistoryPage onNavigate={mockOnNavigate} />);

    expect(screen.getByText('3 conversations')).toBeInTheDocument();
  });

  it('has refresh button', () => {
    render(<HistoryPage onNavigate={mockOnNavigate} />);
    
    expect(screen.getByText('Refresh')).toBeInTheDocument();
  });
});
