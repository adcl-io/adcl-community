/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React from 'react';

/**
 * Nmap Vulnerabilities Component
 * Displays found vulnerabilities
 */
function NmapVulnerabilities({ vulnerabilities }) {
  if (!vulnerabilities || vulnerabilities.length === 0) return null;

  return (
    <div className="nmap-section vulnerability-section">
      <strong>⚠️ Vulnerabilities Found:</strong>
      {vulnerabilities.map((vuln, i) => (
        <div key={i} className="vulnerability-item">
          <div><strong>Port {vuln.port}:</strong> {vuln.script}</div>
          <div className="vuln-finding">{vuln.finding}</div>
        </div>
      ))}
    </div>
  );
}

export default NmapVulnerabilities;
