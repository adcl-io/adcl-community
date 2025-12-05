/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ExecutionPanel from '../ExecutionPanel';

describe('ExecutionPanel', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const mockOnExecute = vi.fn();
  const mockOnCancel = vi.fn();

  it('renders execute button when not executing', () => {
    render(
      <ExecutionPanel
        executing={false}
        onExecute={mockOnExecute}
        disabled={false}
        logs={[]}
        nodeStates={{}}
        totalNodes={3}
      />
    );

    expect(screen.getByText('Execute')).toBeInTheDocument();
  });

  it('disables execute button when disabled prop is true', () => {
    render(
      <ExecutionPanel
        executing={false}
        onExecute={mockOnExecute}
        disabled={true}
        logs={[]}
        nodeStates={{}}
        totalNodes={0}
      />
    );

    const button = screen.getByText('Execute');
    expect(button).toBeDisabled();
  });

  it('shows executing state with spinner', () => {
    render(
      <ExecutionPanel
        executing={true}
        onExecute={mockOnExecute}
        disabled={false}
        logs={[]}
        nodeStates={{}}
        totalNodes={3}
      />
    );

    expect(screen.getByText('Executing...')).toBeInTheDocument();
  });

  it('shows cancel button when executing', () => {
    render(
      <ExecutionPanel
        executing={true}
        onExecute={mockOnExecute}
        onCancel={mockOnCancel}
        disabled={false}
        logs={[]}
        nodeStates={{}}
        totalNodes={3}
      />
    );

    const cancelButton = screen.getByRole('button', { name: '' }); // Icon button
    expect(cancelButton).toBeInTheDocument();
  });

  it('calls onCancel when cancel button is clicked', () => {
    render(
      <ExecutionPanel
        executing={true}
        onExecute={mockOnExecute}
        onCancel={mockOnCancel}
        disabled={false}
        logs={[]}
        nodeStates={{}}
        totalNodes={3}
      />
    );

    const buttons = screen.getAllByRole('button');
    const cancelButton = buttons.find(btn => btn.classList.contains('bg-destructive'));
    fireEvent.click(cancelButton);

    expect(mockOnCancel).toHaveBeenCalled();
  });

  it('shows progress bar when executing', () => {
    render(
      <ExecutionPanel
        executing={true}
        onExecute={mockOnExecute}
        disabled={false}
        logs={[]}
        nodeStates={{ node1: 'completed', node2: 'running', node3: 'pending' }}
        totalNodes={3}
      />
    );

    expect(screen.getByText(/Progress: 1 \/ 3 nodes/)).toBeInTheDocument();
  });

  it('calculates progress correctly', () => {
    render(
      <ExecutionPanel
        executing={true}
        onExecute={mockOnExecute}
        disabled={false}
        logs={[]}
        nodeStates={{ 
          node1: 'completed', 
          node2: 'completed', 
          node3: 'running' 
        }}
        totalNodes={3}
      />
    );

    expect(screen.getByText(/Progress: 2 \/ 3 nodes/)).toBeInTheDocument();
  });

  it('counts error nodes as completed for progress', () => {
    render(
      <ExecutionPanel
        executing={true}
        onExecute={mockOnExecute}
        disabled={false}
        logs={[]}
        nodeStates={{ 
          node1: 'completed', 
          node2: 'error', 
          node3: 'running' 
        }}
        totalNodes={3}
      />
    );

    expect(screen.getByText(/Progress: 2 \/ 3 nodes/)).toBeInTheDocument();
  });

  it('shows execution timer when executing', () => {
    render(
      <ExecutionPanel
        executing={true}
        onExecute={mockOnExecute}
        disabled={false}
        logs={[]}
        nodeStates={{}}
        totalNodes={3}
      />
    );

    // Timer should be visible
    expect(screen.getByText(/\d+[ms]/)).toBeInTheDocument();
  });

  it('timer displays in correct format', () => {
    render(
      <ExecutionPanel
        executing={true}
        onExecute={mockOnExecute}
        disabled={false}
        logs={[]}
        nodeStates={{}}
        totalNodes={3}
      />
    );

    // Should show time in seconds format initially
    const timeElement = screen.getByText(/\d+s/);
    expect(timeElement).toBeInTheDocument();
  });

  it('displays console logs when provided', () => {
    const logs = [
      { timestamp: new Date().toISOString(), level: 'info', message: 'Test log' },
    ];

    render(
      <ExecutionPanel
        executing={false}
        onExecute={mockOnExecute}
        disabled={false}
        logs={logs}
        nodeStates={{}}
        totalNodes={3}
      />
    );

    expect(screen.getByText('Test log')).toBeInTheDocument();
  });

  it('does not show progress when not executing', () => {
    render(
      <ExecutionPanel
        executing={false}
        onExecute={mockOnExecute}
        disabled={false}
        logs={[]}
        nodeStates={{}}
        totalNodes={3}
      />
    );

    expect(screen.queryByText(/Progress:/)).not.toBeInTheDocument();
  });
});
