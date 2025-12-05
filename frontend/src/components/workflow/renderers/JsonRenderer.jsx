/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React from 'react';

/**
 * JSON Result Renderer
 * Generic renderer for JSON data with truncation
 */
function JsonRenderer({ nodeId, data }) {
  if (!data) {
    return (
      <details>
        <summary>📄 {nodeId} (no data)</summary>
        <p>No result data available</p>
      </details>
    );
  }

  // Simple objects (file write results, etc.)
  if (typeof data === 'object' && Object.keys(data).length < 5) {
    return (
      <details>
        <summary>📄 {nodeId}</summary>
        <pre>{JSON.stringify(data, null, 2)}</pre>
      </details>
    );
  }

  // Truncate very large results
  const jsonStr = JSON.stringify(data, null, 2);
  if (jsonStr && jsonStr.length > 10000) {
    return (
      <details>
        <summary>📄 {nodeId} (large result - {(jsonStr.length / 1024).toFixed(1)}KB)</summary>
        <pre>{jsonStr.substring(0, 10000) + '\n\n... (truncated)'}</pre>
      </details>
    );
  }

  // Default JSON view
  return (
    <details>
      <summary>📄 {nodeId}</summary>
      <pre>{jsonStr}</pre>
    </details>
  );
}

export default JsonRenderer;
