/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React from 'react';

/**
 * Agent Result Renderer
 * Displays agent reasoning and analysis
 */
function AgentRenderer({ data }) {
  if (!data || !data.reasoning) {
    return null;
  }

  const reasoning = typeof data.reasoning === 'string'
    ? data.reasoning
    : JSON.stringify(data.reasoning);

  return (
    <div className="agent-result">
      <h4>🤖 Agent Analysis</h4>
      <div className="reasoning-content">{reasoning}</div>
    </div>
  );
}

export default AgentRenderer;
