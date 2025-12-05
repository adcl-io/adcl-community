/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Custom hook for managing MCP server registry
 * Loads and provides access to available MCP servers with their tools
 */
function useMCPRegistry() {
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadServers();
  }, []);

  const loadServers = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch list of servers
      const serversResponse = await axios.get(`${API_URL}/mcp/servers`);
      const serversList = serversResponse.data;
      
      // Fetch tools for each server
      const serversWithTools = await Promise.all(
        serversList.map(async (server) => {
          try {
            const toolsResponse = await axios.get(`${API_URL}/mcp/servers/${server.name}/tools`);
            return {
              ...server,
              tools: toolsResponse.data.tools || [],
            };
          } catch (err) {
            console.error(`Failed to load tools for ${server.name}:`, err);
            return {
              ...server,
              tools: [],
            };
          }
        })
      );
      
      setServers(serversWithTools);
    } catch (err) {
      console.error('Failed to load MCP servers:', err);
      setError(err.message || 'Failed to load servers');
    } finally {
      setLoading(false);
    }
  };

  return {
    servers,
    loading,
    error,
    reload: loadServers,
  };
}

export default useMCPRegistry;
