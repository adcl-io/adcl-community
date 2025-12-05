/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React from 'react';

/**
 * Nmap Summary Component
 * Displays target and port summary
 */
function NmapSummary({ target, summary }) {
  if (!target && !summary) return null;

  return (
    <>
      {target && (
        <div className="nmap-section">
          <strong>Target:</strong> <code>{target}</code>
        </div>
      )}

      {summary && summary.open_ports !== undefined && (
        <div className="nmap-section">
          <strong>Summary:</strong>
          <div className="nmap-stats">
            <span className="stat">Open Ports: {summary.open_ports}</span>
            {summary.open_port_list && (
              <div className="port-list">
                {summary.open_port_list.map((port, i) => (
                  <span key={i} className="port-badge">{port}</span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

export default NmapSummary;
