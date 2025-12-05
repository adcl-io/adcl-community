/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React from 'react';

/**
 * Code Result Renderer
 * Displays generated code with syntax highlighting
 */
function CodeRenderer({ data }) {
  if (!data || !data.code) {
    return null;
  }

  return (
    <div className="code-result">
      <h4>💻 Generated Code</h4>
      <pre><code>{data.code}</code></pre>
    </div>
  );
}

export default CodeRenderer;
