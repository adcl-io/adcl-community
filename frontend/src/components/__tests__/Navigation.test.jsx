/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import Navigation from '../Navigation';
import { mockSessions } from '../../test/mockData';

// Mock the conversation history context
vi.mock('../../contexts/ConversationHistoryContext', () => ({
  useConversationHistoryContext: () => ({
    sessions: mockSessions,
    loadSessions: vi.fn(),
    loadSession: vi.fn()
  })
}));

describe('Navigation', () => {
  const mockOnNavigate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all navigation items', () => {
    render(<Navigation currentPage="playground" onNavigate={mockOnNavigate} />);
    
    expect(screen.getByText('Playground')).toBeInTheDocument();
    expect(screen.getByText('Models')).toBeInTheDocument();
    expect(screen.getByText('MCP Servers')).toBeInTheDocument();
    expect(screen.getByText('Teams')).toBeInTheDocument();
  });

  it('highlights active page', () => {
    render(<Navigation currentPage="playground" onNavigate={mockOnNavigate} />);
    
    const playgroundButton = screen.getByText('Playground').closest('button');
    expect(playgroundButton).toHaveClass('bg-accent');
  });

  it('shows recent conversations when playground is selected', () => {
    render(<Navigation currentPage="playground" onNavigate={mockOnNavigate} />);
    
    expect(screen.getByText('Test Conversation 1')).toBeInTheDocument();
    expect(screen.getByText('Test Conversation 2')).toBeInTheDocument();
  });

  it('hides recent conversations when playground is not selected', () => {
    render(<Navigation currentPage="models" onNavigate={mockOnNavigate} />);
    
    expect(screen.queryByText('Test Conversation 1')).not.toBeInTheDocument();
    expect(screen.queryByText('Test Conversation 2')).not.toBeInTheDocument();
  });

  it('shows "View All History" link when playground selected', () => {
    render(<Navigation currentPage="playground" onNavigate={mockOnNavigate} />);
    
    expect(screen.getByText('View All History')).toBeInTheDocument();
  });

  it('does not show chevron button', () => {
    render(<Navigation currentPage="playground" onNavigate={mockOnNavigate} />);
    
    // Should not have any chevron icons
    const buttons = screen.getAllByRole('button');
    buttons.forEach(button => {
      expect(button.querySelector('svg[class*="chevron"]')).not.toBeInTheDocument();
    });
  });
});
