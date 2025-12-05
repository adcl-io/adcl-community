/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React from 'react';
import NmapRenderer from './NmapRenderer';
import AgentRenderer from './AgentRenderer';
import CodeRenderer from './CodeRenderer';
import JsonRenderer from './JsonRenderer';
import ErrorRenderer from './ErrorRenderer';

/**
 * Detect result type from data structure
 */
function detectResultType(data) {
  if (!data) return 'json';

  // Check for nmap data
  if (data.ports || data.services || data.vulnerabilities || data.summary) {
    return 'nmap';
  }

  // Check for agent reasoning
  if (data.reasoning) {
    return 'agent';
  }

  // Check for code
  if (data.code) {
    return 'code';
  }

  // Default to JSON
  return 'json';
}

/**
 * Result Renderer - Routes to appropriate specialized renderer
 * Detects data type and delegates to focused renderer
 */
function ResultRenderer({ nodeId, data }) {
  try {
    const resultType = detectResultType(data);

    switch (resultType) {
      case 'nmap':
        return <NmapRenderer data={data} />;
      case 'agent':
        return <AgentRenderer data={data} />;
      case 'code':
        return <CodeRenderer data={data} />;
      case 'json':
      default:
        return <JsonRenderer nodeId={nodeId} data={data} />;
    }

  } catch (error) {
    console.error('Error rendering result for', nodeId, error);
    return <ErrorRenderer nodeId={nodeId} error={error} data={data} />;
  }
}

export default ResultRenderer;
