/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ReactFlowProvider } from 'reactflow';
import MCPNode from '../MCPNode';

// Wrapper to provide ReactFlow context
const Wrapper = ({ children }) => (
  <ReactFlowProvider>{children}</ReactFlowProvider>
);

describe('MCPNode', () => {
  const baseData = {
    label: 'agent.think',
    mcp_server: 'agent',
    tool: 'think',
  };

  it('renders node with basic data', () => {
    render(<MCPNode data={baseData} />, { wrapper: Wrapper });
    
    expect(screen.getByText('agent.think')).toBeInTheDocument();
    expect(screen.getByText('agent')).toBeInTheDocument();
    expect(screen.getByText('think')).toBeInTheDocument();
  });

  it('renders idle state by default', () => {
    const { container } = render(<MCPNode data={baseData} />, { wrapper: Wrapper });
    
    const node = container.firstChild;
    expect(node).toHaveClass('border-primary');
  });

  it('renders running state with animation', () => {
    const data = { ...baseData, executionStatus: 'running' };
    const { container } = render(<MCPNode data={data} />, { wrapper: Wrapper });
    
    expect(screen.getByText('RUNNING')).toBeInTheDocument();
    const node = container.firstChild;
    expect(node).toHaveClass('border-yellow-500');
  });

  it('renders completed state', () => {
    const data = { ...baseData, executionStatus: 'completed' };
    const { container } = render(<MCPNode data={data} />, { wrapper: Wrapper });
    
    expect(screen.getByText('COMPLETED')).toBeInTheDocument();
    const node = container.firstChild;
    expect(node).toHaveClass('border-green-500');
  });

  it('renders error state', () => {
    const data = { ...baseData, executionStatus: 'error' };
    const { container } = render(<MCPNode data={data} />, { wrapper: Wrapper });
    
    expect(screen.getByText('ERROR')).toBeInTheDocument();
    const node = container.firstChild;
    expect(node).toHaveClass('border-destructive');
  });

  it('renders pending state', () => {
    const data = { ...baseData, executionStatus: 'pending' };
    const { container } = render(<MCPNode data={data} />, { wrapper: Wrapper });
    
    expect(screen.getByText('PENDING')).toBeInTheDocument();
    const node = container.firstChild;
    expect(node).toHaveClass('border-muted');
  });

  it('does not show status badge for idle state', () => {
    render(<MCPNode data={baseData} />, { wrapper: Wrapper });
    
    expect(screen.queryByText('IDLE')).not.toBeInTheDocument();
  });
});
