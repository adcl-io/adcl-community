/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React from 'react';
import { CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import ResultRenderer from './renderers';

/**
 * Results Viewer Component
 * Displays workflow execution results
 */
function ResultsViewer({ result }) {
  if (!result) return null;

  const getStatusIcon = () => {
    if (result.status === 'completed') {
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    }
    return <XCircle className="h-4 w-4 text-destructive" />;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Results</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className={`flex items-center gap-2 p-3 rounded border-l-4 ${
          result.status === 'completed' 
            ? 'border-l-green-500 bg-green-500/10' 
            : 'border-l-destructive bg-destructive/10'
        }`}>
          {getStatusIcon()}
          <span className="font-medium">Status: {result.status}</span>
        </div>

        {result.errors && result.errors.length > 0 && (
          <Alert variant="destructive">
            <AlertDescription>
              <div className="space-y-1">
                <strong className="flex items-center gap-2">
                  <XCircle className="h-4 w-4" />
                  Errors:
                </strong>
                <ul className="list-disc pl-5 space-y-1">
                  {result.errors.map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              </div>
            </AlertDescription>
          </Alert>
        )}

        {result.results && (
          <div className="space-y-3">
            {Object.entries(result.results).map(([nodeId, data]) => {
              try {
                return <ResultRenderer key={nodeId} nodeId={nodeId} data={data} />;
              } catch (error) {
                console.error(`Error rendering result for ${nodeId}:`, error);
                return (
                  <Alert key={nodeId} variant="destructive">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      <strong>Rendering Error for {nodeId}</strong>
                      <p className="text-sm mt-1">Failed to render result: {error.message}</p>
                    </AlertDescription>
                  </Alert>
                );
              }
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default ResultsViewer;
