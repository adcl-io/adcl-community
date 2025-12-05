/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React from 'react';
import { Terminal, Info, CheckCircle2, XCircle } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';

/**
 * Console Log Component
 * Displays execution logs with auto-scroll
 */
function ConsoleLog({ logs }) {
  const logRef = React.useRef(null);

  // Auto-scroll to bottom on new logs
  React.useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs]);

  if (!logs || logs.length === 0) return null;

  const getLogIcon = (level) => {
    switch (level) {
      case 'success':
        return <CheckCircle2 className="h-3 w-3 text-green-500" />;
      case 'error':
        return <XCircle className="h-3 w-3 text-destructive" />;
      default:
        return <Info className="h-3 w-3 text-primary" />;
    }
  };

  const getLogColor = (level) => {
    switch (level) {
      case 'success':
        return 'text-green-500 font-semibold';
      case 'error':
        return 'text-destructive font-semibold';
      default:
        return 'text-muted-foreground';
    }
  };

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium flex items-center gap-2">
        <Terminal className="h-4 w-4" />
        Execution Console
      </h3>
      <ScrollArea className="h-[300px] rounded border border-border bg-muted/50">
        <div className="p-2 space-y-1 font-mono text-xs" ref={logRef}>
          {logs.map((log, index) => (
            <div key={index} className="flex items-start gap-2 py-1 border-b border-border/50 last:border-0">
              {getLogIcon(log.level)}
              <span className="text-muted-foreground min-w-[70px] flex-shrink-0">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
              <span className={`flex-1 ${getLogColor(log.level)}`}>
                {log.message}
              </span>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}

export default ConsoleLog;
