/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import NodePalette from '../NodePalette';

describe('NodePalette', () => {
  const mockServers = [
    {
      name: 'agent',
      description: 'AI Agent',
      tools: [
        { name: 'think', description: 'Analyze problems' },
        { name: 'code', description: 'Generate code' },
      ],
    },
    {
      name: 'file_tools',
      description: 'File operations',
      tools: [
        { name: 'read_file', description: 'Read files' },
        { name: 'write_file', description: 'Write files' },
      ],
    },
  ];

  it('renders loading state', () => {
    render(<NodePalette servers={[]} loading={true} error={null} />);
    expect(screen.getByText('Loading servers...')).toBeInTheDocument();
  });

  it('renders error state', () => {
    render(<NodePalette servers={[]} loading={false} error="Failed to load" />);
    expect(screen.getByText(/Failed to load/)).toBeInTheDocument();
  });

  it('renders empty state', () => {
    render(<NodePalette servers={[]} loading={false} error={null} />);
    expect(screen.getByText('No servers available')).toBeInTheDocument();
  });

  it('renders servers with tools', () => {
    render(<NodePalette servers={mockServers} loading={false} error={null} />);
    
    // Check server names
    expect(screen.getByText('agent')).toBeInTheDocument();
    expect(screen.getByText('file_tools')).toBeInTheDocument();
    
    // Check tool names
    expect(screen.getByText('think')).toBeInTheDocument();
    expect(screen.getByText('code')).toBeInTheDocument();
    expect(screen.getByText('read_file')).toBeInTheDocument();
    expect(screen.getByText('write_file')).toBeInTheDocument();
  });

  it('displays tool count badges', () => {
    render(<NodePalette servers={mockServers} loading={false} error={null} />);
    
    const badges = screen.getAllByText('2');
    expect(badges).toHaveLength(2); // Both servers have 2 tools
  });

  it('makes tools draggable', () => {
    render(<NodePalette servers={mockServers} loading={false} error={null} />);
    
    const thinkTool = screen.getByText('think').parentElement.parentElement;
    expect(thinkTool).toHaveAttribute('draggable', 'true');
  });

  it('calls onDragStart with correct data', () => {
    const mockDataTransfer = {
      setData: vi.fn(),
      effectAllowed: '',
    };

    render(<NodePalette servers={mockServers} loading={false} error={null} />);
    
    const thinkTool = screen.getByText('think').closest('div');
    const dragEvent = new Event('dragstart', { bubbles: true });
    Object.defineProperty(dragEvent, 'dataTransfer', {
      value: mockDataTransfer,
    });

    thinkTool.dispatchEvent(dragEvent);

    expect(mockDataTransfer.setData).toHaveBeenCalledWith(
      'application/reactflow',
      expect.stringContaining('agent')
    );
  });
});
