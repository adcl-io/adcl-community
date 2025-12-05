/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import axios from 'axios';
import useMCPRegistry from '../useMCPRegistry';

vi.mock('axios');

describe('useMCPRegistry', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches servers and tools on mount', async () => {
    const mockServers = [
      { name: 'agent', endpoint: 'http://localhost:7000', description: 'AI Agent' },
      { name: 'file_tools', endpoint: 'http://localhost:7002', description: 'File tools' },
    ];

    const mockAgentTools = {
      tools: [
        { name: 'think', description: 'Analyze' },
        { name: 'code', description: 'Generate code' },
      ],
    };

    const mockFileTools = {
      tools: [
        { name: 'read_file', description: 'Read' },
        { name: 'write_file', description: 'Write' },
      ],
    };

    axios.get.mockImplementation((url) => {
      if (url.includes('/mcp/servers')) {
        return Promise.resolve({ data: mockServers });
      }
      if (url.includes('/agent/tools')) {
        return Promise.resolve({ data: mockAgentTools });
      }
      if (url.includes('/file_tools/tools')) {
        return Promise.resolve({ data: mockFileTools });
      }
    });

    const { result } = renderHook(() => useMCPRegistry());

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.servers).toHaveLength(2);
    expect(result.current.servers[0].tools).toBeDefined();
    expect(result.current.servers[1].tools).toBeDefined();
    expect(result.current.error).toBeNull();
  });

  it('handles server fetch error', async () => {
    axios.get.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useMCPRegistry());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe('Network error');
    expect(result.current.servers).toEqual([]);
  });

  it('handles tools fetch error gracefully', async () => {
    const mockServers = [
      { name: 'agent', endpoint: 'http://localhost:7000', description: 'AI Agent' },
    ];

    axios.get.mockImplementation((url) => {
      if (url.includes('/mcp/servers')) {
        return Promise.resolve({ data: mockServers });
      }
      if (url.includes('/agent/tools')) {
        return Promise.reject(new Error('Tools error'));
      }
    });

    const { result } = renderHook(() => useMCPRegistry());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.servers).toHaveLength(1);
    expect(result.current.servers[0].tools).toEqual([]);
    expect(result.current.error).toBeNull();
  });

  it('provides reload function', async () => {
    const mockServers = [
      { name: 'agent', endpoint: 'http://localhost:7000', description: 'AI Agent' },
    ];

    const mockTools = {
      tools: [{ name: 'think', description: 'Analyze' }],
    };

    axios.get.mockImplementation((url) => {
      if (url.includes('/mcp/servers')) {
        return Promise.resolve({ data: mockServers });
      }
      if (url.includes('/agent/tools')) {
        return Promise.resolve({ data: mockTools });
      }
    });

    const { result } = renderHook(() => useMCPRegistry());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(axios.get).toHaveBeenCalledTimes(2); // servers + tools

    // Call reload
    result.current.reload();

    await waitFor(() => {
      expect(axios.get).toHaveBeenCalledTimes(4); // servers + tools again
    });
  });
});
