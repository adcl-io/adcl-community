/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React from 'react';
import { Server, Loader2, AlertCircle, GripVertical } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

/**
 * Node Palette Component
 * Displays available MCP servers and tools with drag-and-drop support
 */
function NodePalette({ servers, loading, error }) {
  const onDragStart = (event, server, tool) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify({
      mcpServer: server.name,
      tool: tool.name,
    }));
    event.dataTransfer.effectAllowed = 'move';
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-4 w-4" />
            MCP Servers
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading servers...
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-4 w-4" />
            MCP Servers
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-destructive">
            <AlertCircle className="h-4 w-4" />
            Error: {error}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Server className="h-4 w-4" />
          MCP Servers
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {servers.length === 0 ? (
          <p className="text-sm text-muted-foreground">No servers available</p>
        ) : (
          servers.map((server) => (
            <div key={server.name} className="space-y-1">
              <div className="flex items-center justify-between px-3 py-2 rounded-md bg-muted/50">
                <div className="flex flex-col gap-1">
                  <span className="font-medium text-sm">{server.name}</span>
                  <span className="text-xs text-muted-foreground">{server.description}</span>
                </div>
                {server.tools && (
                  <Badge variant="secondary">{server.tools.length}</Badge>
                )}
              </div>
              
              {server.tools && server.tools.length > 0 && (
                <div className="ml-3 space-y-1">
                  {server.tools.map((tool) => (
                    <div
                      key={tool.name}
                      draggable
                      onDragStart={(e) => onDragStart(e, server, tool)}
                      className="flex items-center gap-2 p-2 rounded border border-border hover:bg-accent hover:border-primary cursor-grab active:cursor-grabbing transition-colors"
                    >
                      <GripVertical className="h-3 w-3 text-muted-foreground" />
                      <div className="flex-1">
                        <span className="text-xs font-medium">{tool.name}</span>
                        {tool.description && (
                          <p className="text-xs text-muted-foreground line-clamp-1">
                            {tool.description}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

export default NodePalette;
