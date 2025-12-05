/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React from 'react';
import { Handle, Position } from 'reactflow';
import { Clock, Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

/**
 * Custom MCP Node Component
 * Displays a node in the workflow canvas with execution state
 * Double-click to edit parameters
 */
function MCPNode({ data, id }) {
  const status = data.executionStatus || 'idle';
  
  const statusConfig = {
    idle: {
      icon: <Clock className="h-4 w-4 text-muted-foreground" />,
      borderColor: 'border-primary',
      bgColor: 'bg-card',
      headerBg: 'bg-primary',
      headerText: 'text-primary-foreground'
    },
    pending: {
      icon: <Clock className="h-4 w-4 text-muted-foreground" />,
      borderColor: 'border-muted',
      bgColor: 'bg-card',
      headerBg: 'bg-muted',
      headerText: 'text-muted-foreground'
    },
    running: {
      icon: <Loader2 className="h-4 w-4 animate-spin text-yellow-500" />,
      borderColor: 'border-yellow-500',
      bgColor: 'bg-card',
      headerBg: 'bg-yellow-500',
      headerText: 'text-black',
      shadow: 'shadow-lg shadow-yellow-500/50'
    },
    completed: {
      icon: <CheckCircle2 className="h-4 w-4 text-green-500" />,
      borderColor: 'border-green-500',
      bgColor: 'bg-card',
      headerBg: 'bg-green-500',
      headerText: 'text-white',
      shadow: 'shadow-lg shadow-green-500/30'
    },
    error: {
      icon: <XCircle className="h-4 w-4 text-destructive" />,
      borderColor: 'border-destructive',
      bgColor: 'bg-card',
      headerBg: 'bg-destructive',
      headerText: 'text-destructive-foreground',
      shadow: 'shadow-lg shadow-destructive/50'
    }
  };

  const config = statusConfig[status];

  const handleDoubleClick = () => {
    if (data.onNodeDoubleClick) {
      data.onNodeDoubleClick(id, data);
    }
  };

  return (
    <div 
      onDoubleClick={handleDoubleClick}
      className={`
      ${config.bgColor} 
      border-2 ${config.borderColor} 
      rounded-lg 
      min-w-[200px] 
      text-sm
      ${config.shadow || ''}
      transition-all duration-200
    `}>
      <Handle 
        type="target" 
        position={Position.Top} 
        id="input"
        className="!w-3 !h-3 !bg-primary !border-2 !border-background"
      />
      
      <div className={`
        ${config.headerBg} 
        ${config.headerText}
        px-3 py-2 
        rounded-t-md 
        font-semibold 
        flex 
        justify-between 
        items-center
      `}>
        <span>{data.label}</span>
        {config.icon}
      </div>
      
      <div className="p-3 space-y-2">
        <div className="flex items-center gap-2 text-xs">
          <span className="text-muted-foreground font-medium">Server:</span>
          <Badge variant="secondary" className="text-xs font-mono">
            {data.mcp_server}
          </Badge>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="text-muted-foreground font-medium">Tool:</span>
          <Badge variant="secondary" className="text-xs font-mono">
            {data.tool}
          </Badge>
        </div>
        {status !== 'idle' && (
          <div className="pt-2 border-t border-border text-center">
            <Badge variant="outline" className="text-xs font-semibold">
              {status.toUpperCase()}
            </Badge>
          </div>
        )}
      </div>
      
      <Handle 
        type="source" 
        position={Position.Bottom} 
        id="output"
        className="!w-3 !h-3 !bg-primary !border-2 !border-background"
      />
    </div>
  );
}

export default MCPNode;
