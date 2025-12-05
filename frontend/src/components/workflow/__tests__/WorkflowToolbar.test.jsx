/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, test, expect, beforeEach, vi } from 'vitest';
import '@testing-library/jest-dom';
import WorkflowToolbar from '../WorkflowToolbar';

describe('WorkflowToolbar', () => {
  const mockOnSave = vi.fn();
  const mockOnLoad = vi.fn();
  const mockOnListWorkflows = vi.fn();
  const mockOnDeleteWorkflow = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('renders save and load buttons', () => {
    render(
      <WorkflowToolbar
        onSave={mockOnSave}
        onLoad={mockOnLoad}
        onListWorkflows={mockOnListWorkflows}
        onDeleteWorkflow={mockOnDeleteWorkflow}
      />
    );

    expect(screen.getByText('Save Workflow')).toBeInTheDocument();
    expect(screen.getByText('Load Workflow')).toBeInTheDocument();
  });

  test('opens save dialog when save button clicked', () => {
    render(
      <WorkflowToolbar
        onSave={mockOnSave}
        onLoad={mockOnLoad}
        onListWorkflows={mockOnListWorkflows}
        onDeleteWorkflow={mockOnDeleteWorkflow}
      />
    );

    fireEvent.click(screen.getByText('Save Workflow'));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByLabelText('Workflow Name')).toBeInTheDocument();
  });

  test('save button disabled when name is empty', () => {
    render(
      <WorkflowToolbar
        onSave={mockOnSave}
        onLoad={mockOnLoad}
        onListWorkflows={mockOnListWorkflows}
        onDeleteWorkflow={mockOnDeleteWorkflow}
      />
    );

    fireEvent.click(screen.getByText('Save Workflow'));
    const saveButton = screen.getAllByText('Save').find(el => el.tagName === 'BUTTON');
    expect(saveButton).toBeDisabled();
  });

  test('calls onSave with name and description', async () => {
    mockOnSave.mockResolvedValue({});
    
    render(
      <WorkflowToolbar
        onSave={mockOnSave}
        onLoad={mockOnLoad}
        onListWorkflows={mockOnListWorkflows}
        onDeleteWorkflow={mockOnDeleteWorkflow}
      />
    );

    fireEvent.click(screen.getByText('Save Workflow'));
    
    fireEvent.change(screen.getByLabelText('Workflow Name'), {
      target: { value: 'Test Workflow' }
    });
    fireEvent.change(screen.getByLabelText('Description (optional)'), {
      target: { value: 'Test description' }
    });

    const saveButton = screen.getAllByText('Save').find(el => el.tagName === 'BUTTON');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockOnSave).toHaveBeenCalledWith('Test Workflow', 'Test description');
    });
  });

  test('opens load dialog and lists workflows', async () => {
    mockOnListWorkflows.mockResolvedValue([
      { name: 'Workflow 1', filename: 'workflow1.json', description: 'First' },
      { name: 'Workflow 2', filename: 'workflow2.json', description: '' }
    ]);

    render(
      <WorkflowToolbar
        onSave={mockOnSave}
        onLoad={mockOnLoad}
        onListWorkflows={mockOnListWorkflows}
        onDeleteWorkflow={mockOnDeleteWorkflow}
      />
    );

    fireEvent.click(screen.getByText('Load Workflow'));

    await waitFor(() => {
      expect(mockOnListWorkflows).toHaveBeenCalled();
      expect(screen.getByText('Workflow 1')).toBeInTheDocument();
      expect(screen.getByText('Workflow 2')).toBeInTheDocument();
    });
  });

  test('calls onLoad when workflow clicked', async () => {
    mockOnListWorkflows.mockResolvedValue([
      { name: 'Test Workflow', filename: 'test.json', description: '' }
    ]);
    mockOnLoad.mockResolvedValue({});

    render(
      <WorkflowToolbar
        onSave={mockOnSave}
        onLoad={mockOnLoad}
        onListWorkflows={mockOnListWorkflows}
        onDeleteWorkflow={mockOnDeleteWorkflow}
      />
    );

    fireEvent.click(screen.getByText('Load Workflow'));

    await waitFor(() => {
      expect(screen.getByText('Test Workflow')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Test Workflow'));

    await waitFor(() => {
      expect(mockOnLoad).toHaveBeenCalledWith('test.json');
    });
  });
});
