/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React from 'react';

/**
 * Nmap OS Detection Component
 * Displays operating system matches
 */
function NmapOsDetection({ osMatches }) {
  if (!osMatches || osMatches.length === 0) return null;

  return (
    <div className="nmap-section">
      <strong>OS Detection:</strong>
      <ul className="os-list">
        {osMatches.slice(0, 3).map((os, i) => (
          <li key={i}>
            {os.name} <span className="accuracy">({os.accuracy}% accuracy)</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default NmapOsDetection;
