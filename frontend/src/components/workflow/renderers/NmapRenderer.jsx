/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React from 'react';
import NmapSummary from './nmap/NmapSummary';
import NmapServices from './nmap/NmapServices';
import NmapVulnerabilities from './nmap/NmapVulnerabilities';
import NmapOsDetection from './nmap/NmapOsDetection';

/**
 * Nmap Result Renderer
 * Orchestrates display of network scan results
 */
function NmapRenderer({ data }) {
  if (!data || !(data.ports || data.services || data.vulnerabilities || data.summary)) {
    return null;
  }

  return (
    <div className="nmap-results">
      <h3>🔍 Network Scan Results</h3>
      <NmapSummary target={data.target} summary={data.summary} />
      <NmapServices services={data.services} />
      <NmapVulnerabilities vulnerabilities={data.vulnerabilities} />
      <NmapOsDetection osMatches={data.os_matches} />
    </div>
  );
}

export default NmapRenderer;
