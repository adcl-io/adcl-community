/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React, { useState, useEffect } from 'react';
import { Play, Loader2, X, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import ConsoleLog from './ConsoleLog';

/**
 * Execution Panel Component
 * Controls workflow execution and displays console logs with progress
 */
function ExecutionPanel({ executing, onExecute, onCancel, disabled, logs, nodeStates, totalNodes }) {
  const [executionTime, setExecutionTime] = useState(0);
  const [startTime, setStartTime] = useState(null);

  // Calculate progress based on node states
  const completedNodes = nodeStates ? 
    Object.values(nodeStates).filter(state => state === 'completed' || state === 'error').length : 0;
  const progress = totalNodes > 0 ? (completedNodes / totalNodes) * 100 : 0;

  // Track execution time
  useEffect(() => {
    if (executing && !startTime) {
      setStartTime(Date.now());
      setExecutionTime(0);
    }

    if (executing) {
      const interval = setInterval(() => {
        setExecutionTime(Math.floor((Date.now() - startTime) / 1000));
      }, 1000);
      return () => clearInterval(interval);
    } else {
      setStartTime(null);
    }
  }, [executing, startTime]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Actions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button
              onClick={onExecute}
              disabled={disabled || executing}
              className="flex-1"
            >
              {executing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Executing...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  Execute
                </>
              )}
            </Button>
            
            {executing && onCancel && (
              <Button
                onClick={onCancel}
                variant="destructive"
                size="icon"
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>

          {executing && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  Progress: {completedNodes} / {totalNodes} nodes
                </span>
                <span className="flex items-center gap-1 text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  {formatTime(executionTime)}
                </span>
              </div>
              <Progress value={progress} className="h-2" />
            </div>
          )}
        </CardContent>
      </Card>

      {logs && logs.length > 0 && (
        <Card>
          <CardContent className="pt-6">
            <ConsoleLog logs={logs} />
          </CardContent>
        </Card>
      )}
    </>
  );
}

export default ExecutionPanel;
