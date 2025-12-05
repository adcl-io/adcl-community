/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import {
  Wrench,
  RefreshCw,
  Loader2,
  Search,
  Package,
  FolderOpen,
  Database,
  Plug,
  CheckCircle2,
  ChevronDown,
  ChevronRight
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function MCPServersPage() {
  const [servers, setServers] = useState([]);
  const [serverTools, setServerTools] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [loadingTools, setLoadingTools] = useState({});
  const [expandedTools, setExpandedTools] = useState({});

  useEffect(() => {
    loadServers();
  }, []);

  const loadServers = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API_URL}/mcp/servers`);
      setServers(response.data);

      // Load tools for each server
      response.data.forEach(server => {
        loadServerTools(server.name);
      });
    } catch (error) {
      console.error('Failed to load servers:', error);
      setError('Failed to load MCP servers. Please make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const loadServerTools = async (serverName) => {
    setLoadingTools(prev => ({ ...prev, [serverName]: true }));
    try {
      const response = await axios.get(`${API_URL}/mcp/servers/${serverName}/tools`);
      // API returns { tools: [...] }, extract the array
      const tools = response.data.tools || response.data || [];
      setServerTools(prev => ({ ...prev, [serverName]: tools }));
    } catch (error) {
      console.error(`Failed to load tools for ${serverName}:`, error);
      setServerTools(prev => ({ ...prev, [serverName]: [] }));
    } finally {
      setLoadingTools(prev => ({ ...prev, [serverName]: false }));
    }
  };

  const getServerIcon = (serverName) => {
    const name = serverName.toLowerCase();
    if (name.includes('nmap')) return Search;
    if (name.includes('git')) return Package;
    if (name.includes('file')) return FolderOpen;
    if (name.includes('db') || name.includes('database')) return Database;
    if (name.includes('api')) return Plug;
    return Wrench;
  };

  const toggleToolExpansion = (serverName, toolIndex) => {
    const key = `${serverName}-${toolIndex}`;
    setExpandedTools(prev => ({ ...prev, [key]: !prev[key] }));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-7xl mx-auto">
          <div className="mb-8 flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold text-foreground flex items-center gap-2">
                <Wrench className="h-8 w-8" />
                MCP Servers
              </h1>
              <p className="text-destructive mt-1 font-medium">{error}</p>
            </div>
            <Button onClick={loadServers}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8 flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-foreground flex items-center gap-2">
              <Wrench className="h-8 w-8" />
              MCP Servers
            </h1>
            <p className="text-muted-foreground mt-1">Available Model Context Protocol servers and their tools</p>
          </div>
          <Button onClick={loadServers}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>

        {servers.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-16">
              <Wrench className="h-16 w-16 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold text-foreground mb-2">No MCP Servers Found</h3>
              <p className="text-muted-foreground text-sm">Configure MCP servers in your backend to see them here.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {servers.map(server => {
              const ServerIcon = getServerIcon(server.name);
              return (
                <Card key={server.name} className="hover:shadow-lg transition-all">
                  <CardHeader>
                    <div className="flex items-start gap-4">
                      <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                        <ServerIcon className="h-6 w-6 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <CardTitle className="text-lg">{server.name}</CardTitle>
                          <Badge variant="outline" className="bg-success/10 text-success border-success/30">
                            <CheckCircle2 className="h-3 w-3 mr-1" />
                            Connected
                          </Badge>
                        </div>
                        <div className="mt-1">
                          <Badge variant="secondary" className="font-mono text-xs">
                            {server.endpoint}
                          </Badge>
                        </div>
                      </div>
                    </div>
                    <div className="mt-3">
                      <Badge variant="outline" className="font-mono text-xs">
                        v{server.version || '1.0.0'}
                      </Badge>
                    </div>
                  </CardHeader>

                  {server.description && (
                    <CardContent className="pt-0 pb-4">
                      <p className="text-sm text-muted-foreground">{server.description}</p>
                    </CardContent>
                  )}

                  <CardContent className="pt-0">
                    <div className="border-t pt-4">
                      <h4 className="text-sm font-semibold text-foreground mb-3">Available Tools</h4>
                      {loadingTools[server.name] ? (
                        <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
                          Loading tools...
                        </div>
                      ) : serverTools[server.name] && serverTools[server.name].length > 0 ? (
                        <div className="space-y-2">
                          {serverTools[server.name].map((tool, index) => {
                            const key = `${server.name}-${index}`;
                            const isExpanded = expandedTools[key];
                            return (
                              <Collapsible
                                key={index}
                                open={isExpanded}
                                onOpenChange={() => toggleToolExpansion(server.name, index)}
                              >
                                <Card className="border-l-4 border-l-primary hover:bg-accent/50 transition-colors">
                                  <CollapsibleTrigger className="w-full">
                                    <CardHeader className="p-3">
                                      <div className="flex items-center justify-between">
                                        <code className="text-xs font-semibold bg-primary/10 text-primary px-2 py-1 rounded">
                                          {tool.name}
                                        </code>
                                        {isExpanded ? (
                                          <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                        ) : (
                                          <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                        )}
                                      </div>
                                      {tool.description && (
                                        <p className="text-xs text-muted-foreground mt-2 text-left">
                                          {tool.description}
                                        </p>
                                      )}
                                    </CardHeader>
                                  </CollapsibleTrigger>
                                  <CollapsibleContent>
                                    {tool.input_schema && tool.input_schema.properties && (
                                      <CardContent className="p-3 pt-0 border-t">
                                        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                                          Parameters:
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                          {Object.entries(tool.input_schema.properties).map(([paramName, paramInfo]) => (
                                            <Badge
                                              key={paramName}
                                              variant="outline"
                                              className="font-mono text-xs cursor-help bg-card hover:bg-accent hover:border-primary"
                                              title={paramInfo.description}
                                            >
                                              {paramName}
                                              {tool.input_schema.required?.includes(paramName) && (
                                                <span className="text-destructive ml-1">*</span>
                                              )}
                                            </Badge>
                                          ))}
                                        </div>
                                      </CardContent>
                                    )}
                                  </CollapsibleContent>
                                </Card>
                              </Collapsible>
                            );
                          })}
                        </div>
                      ) : (
                        <div className="text-center py-8 text-sm text-muted-foreground bg-muted rounded-md">
                          No tools available
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
