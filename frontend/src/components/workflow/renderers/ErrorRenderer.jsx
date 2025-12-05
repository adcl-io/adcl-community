/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React from 'react';

/**
 * Error Renderer
 * Displays rendering errors with fallback
 */
function ErrorRenderer({ nodeId, error, data }) {
  return (
    <div className="agent-result">
      <h4>⚠️ Rendering Error for {nodeId}</h4>
      <p>Could not render result: {error?.message || 'Unknown error'}</p>
      <details>
        <summary>Raw data</summary>
        <pre>{String(data)}</pre>
      </details>
    </div>
  );
}

export default ErrorRenderer;
