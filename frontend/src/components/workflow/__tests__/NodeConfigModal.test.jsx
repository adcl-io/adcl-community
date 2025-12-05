/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import NodeConfigModal from '../NodeConfigModal';

describe('NodeConfigModal', () => {
  const mockNode = {
    id: 'node-1',
    data: {
      label: 'agent.think',
      mcp_server: 'agent',
      tool: 'think',
      params: {
        prompt: 'Test prompt',
      },
    },
  };

  const mockToolSchema = {
    name: 'think',
    description: 'Analyze problems',
    input_schema: {
      type: 'object',
      properties: {
        prompt: {
          type: 'string',
          description: 'The problem to analyze',
        },
        context: {
          type: 'string',
          description: 'Additional context',
        },
      },
      required: ['prompt'],
    },
  };

  const mockOnClose = vi.fn();
  const mockOnSave = vi.fn();

  it('renders modal when open', () => {
    render(
      <NodeConfigModal
        node={mockNode}
        toolSchema={mockToolSchema}
        open={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    );

    expect(screen.getByText('Configure Node')).toBeInTheDocument();
    expect(screen.getByText('agent.think')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(
      <NodeConfigModal
        node={mockNode}
        toolSchema={mockToolSchema}
        open={false}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    );

    expect(screen.queryByText('Configure Node')).not.toBeInTheDocument();
  });

  it('displays form fields from schema', () => {
    render(
      <NodeConfigModal
        node={mockNode}
        toolSchema={mockToolSchema}
        open={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    );

    expect(screen.getByLabelText(/prompt/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/context/i)).toBeInTheDocument();
  });

  it('shows required field indicator', () => {
    render(
      <NodeConfigModal
        node={mockNode}
        toolSchema={mockToolSchema}
        open={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    );

    const promptLabel = screen.getByText('prompt');
    expect(promptLabel.parentElement.textContent).toContain('*');
  });

  it('populates fields with existing params', () => {
    render(
      <NodeConfigModal
        node={mockNode}
        toolSchema={mockToolSchema}
        open={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    );

    const promptInput = screen.getByLabelText(/prompt/i);
    expect(promptInput).toHaveValue('Test prompt');
  });

  it('validates required fields on save', async () => {
    const nodeWithoutParams = {
      ...mockNode,
      data: { ...mockNode.data, params: {} },
    };

    render(
      <NodeConfigModal
        node={nodeWithoutParams}
        toolSchema={mockToolSchema}
        open={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    );

    const saveButton = screen.getByText('Save Changes');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText('This field is required')).toBeInTheDocument();
    });

    expect(mockOnSave).not.toHaveBeenCalled();
  });

  it('calls onSave with updated params when valid', async () => {
    const user = userEvent.setup();

    render(
      <NodeConfigModal
        node={mockNode}
        toolSchema={mockToolSchema}
        open={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    );

    const promptInput = screen.getByLabelText(/prompt/i);
    await user.clear(promptInput);
    await user.type(promptInput, 'Updated prompt');

    const saveButton = screen.getByText('Save Changes');
    await user.click(saveButton);

    expect(mockOnSave).toHaveBeenCalledWith('node-1', expect.objectContaining({
      prompt: 'Updated prompt',
    }));
  });

  it('calls onClose when cancel is clicked', async () => {
    const user = userEvent.setup();

    render(
      <NodeConfigModal
        node={mockNode}
        toolSchema={mockToolSchema}
        open={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    );

    const cancelButton = screen.getByText('Cancel');
    await user.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('clears errors when field is edited', async () => {
    const user = userEvent.setup();
    const nodeWithoutParams = {
      ...mockNode,
      data: { ...mockNode.data, params: {} },
    };

    render(
      <NodeConfigModal
        node={nodeWithoutParams}
        toolSchema={mockToolSchema}
        open={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    );

    // Trigger validation error
    const saveButton = screen.getByText('Save Changes');
    await user.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText('This field is required')).toBeInTheDocument();
    });

    // Edit field
    const promptInput = screen.getByLabelText(/prompt/i);
    await user.type(promptInput, 'New value');

    // Error should be cleared
    await waitFor(() => {
      expect(screen.queryByText('This field is required')).not.toBeInTheDocument();
    });
  });

  it('shows message when tool has no parameters', () => {
    const schemaWithoutParams = {
      ...mockToolSchema,
      input_schema: {
        type: 'object',
        properties: {},
      },
    };

    render(
      <NodeConfigModal
        node={mockNode}
        toolSchema={schemaWithoutParams}
        open={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    );

    expect(screen.getByText('This tool has no configurable parameters.')).toBeInTheDocument();
  });
});
