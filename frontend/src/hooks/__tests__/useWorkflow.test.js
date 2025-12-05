/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import { renderHook, act } from '@testing-library/react';
import { describe, test, expect, beforeEach, vi } from 'vitest';
import axios from 'axios';
import useWorkflow from '../useWorkflow';

vi.mock('axios');

describe('useWorkflow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('saveWorkflow converts nodes/edges to workflow JSON', async () => {
    axios.post.mockResolvedValue({ data: { message: 'Workflow saved', filename: 'test.json' } });

    const { result } = renderHook(() => useWorkflow());

    // Add nodes and edges
    act(() => {
      result.current.addNode('agent', 'think', { x: 100, y: 100 });
    });

    await act(async () => {
      await result.current.saveWorkflow('Test Workflow', 'Test description');
    });

    expect(axios.post).toHaveBeenCalledWith(
      expect.stringContaining('/workflows'),
      expect.objectContaining({
        name: 'Test Workflow',
        description: 'Test description',
        nodes: expect.arrayContaining([
          expect.objectContaining({
            type: 'mcp_call',
            mcp_server: 'agent',
            tool: 'think'
          })
        ]),
        edges: expect.any(Array)
      })
    );
  });

  test('loadWorkflow fetches and converts to ReactFlow format', async () => {
    const mockWorkflow = {
      name: 'Test Workflow',
      nodes: [
        { id: 'node-1', type: 'mcp_call', mcp_server: 'agent', tool: 'think', params: {} }
      ],
      edges: [{ source: 'node-1', target: 'node-2' }]
    };

    axios.get.mockResolvedValue({ data: mockWorkflow });

    const { result } = renderHook(() => useWorkflow());

    await act(async () => {
      await result.current.loadWorkflow('test.json');
    });

    expect(axios.get).toHaveBeenCalledWith(expect.stringContaining('/workflows/test.json'));
    expect(result.current.nodes).toHaveLength(1);
    expect(result.current.nodes[0]).toMatchObject({
      id: 'node-1',
      type: 'mcpNode',
      data: {
        mcp_server: 'agent',
        tool: 'think'
      }
    });
  });

  test('listWorkflows fetches all workflows', async () => {
    const mockWorkflows = [
      { name: 'Workflow 1', filename: 'w1.json', description: 'First' },
      { name: 'Workflow 2', filename: 'w2.json', description: 'Second' }
    ];

    axios.get.mockResolvedValue({ data: mockWorkflows });

    const { result } = renderHook(() => useWorkflow());

    let workflows;
    await act(async () => {
      workflows = await result.current.listWorkflows();
    });

    expect(axios.get).toHaveBeenCalledWith(expect.stringContaining('/workflows'));
    expect(workflows).toEqual(mockWorkflows);
  });

  test('deleteWorkflow calls DELETE endpoint', async () => {
    axios.delete.mockResolvedValue({ data: { message: 'Workflow deleted' } });

    const { result } = renderHook(() => useWorkflow());

    await act(async () => {
      await result.current.deleteWorkflow('test.json');
    });

    expect(axios.delete).toHaveBeenCalledWith(expect.stringContaining('/workflows/test.json'));
  });

  test('updateNodeParams updates node parameters', () => {
    const { result } = renderHook(() => useWorkflow());

    act(() => {
      result.current.addNode('agent', 'think', { x: 100, y: 100 });
    });

    const nodeId = result.current.nodes[0].id;

    act(() => {
      result.current.updateNodeParams(nodeId, { prompt: 'test prompt' });
    });

    expect(result.current.nodes[0].data.params).toEqual({ prompt: 'test prompt' });
  });

  test('clearWorkflow removes all nodes and edges', () => {
    const { result } = renderHook(() => useWorkflow());

    act(() => {
      result.current.addNode('agent', 'think', { x: 100, y: 100 });
      result.current.addNode('agent', 'code', { x: 200, y: 100 });
    });

    expect(result.current.nodes).toHaveLength(2);

    act(() => {
      result.current.clearWorkflow();
    });

    expect(result.current.nodes).toHaveLength(0);
    expect(result.current.edges).toHaveLength(0);
  });
});
