/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React from 'react';

/**
 * Nmap Services Component
 * Displays detected services in table format
 */
function NmapServices({ services }) {
  if (!services || services.length === 0) return null;

  return (
    <div className="nmap-section">
      <strong>Detected Services:</strong>
      <table className="service-table">
        <thead>
          <tr>
            <th>Port</th>
            <th>Service</th>
            <th>Version</th>
          </tr>
        </thead>
        <tbody>
          {services.map((svc, i) => {
            const serviceName = typeof svc.service === 'object'
              ? svc.service.name
              : svc.service;

            const version = typeof svc.service === 'object'
              ? (svc.service.version || svc.service.product || 'N/A')
              : (svc.version || 'N/A');

            return (
              <tr key={i}>
                <td><code>{svc.port}</code></td>
                <td>{serviceName}</td>
                <td>{version}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default NmapServices;
