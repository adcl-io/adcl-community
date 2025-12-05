/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

/**
 * Workflow Validation Utilities
 * Validates workflow structure, prevents cycles, checks parameters
 */

/**
 * Detect cycles in workflow using DFS
 * Returns true if cycle exists
 */
function hasCycles(nodes, edges) {
  if (nodes.length === 0) return false;

  // Build adjacency list
  const graph = {};
  nodes.forEach(node => {
    graph[node.id] = [];
  });

  edges.forEach(edge => {
    if (graph[edge.source]) {
      graph[edge.source].push(edge.target);
    }
  });

  // Track visited nodes and recursion stack
  const visited = new Set();
  const recStack = new Set();

  function dfs(nodeId) {
    visited.add(nodeId);
    recStack.add(nodeId);

    const neighbors = graph[nodeId] || [];
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        if (dfs(neighbor)) {
          return true; // Cycle found
        }
      } else if (recStack.has(neighbor)) {
        return true; // Back edge found - cycle!
      }
    }

    recStack.delete(nodeId);
    return false;
  }

  // Check each node (handles disconnected components)
  for (const nodeId of Object.keys(graph)) {
    if (!visited.has(nodeId)) {
      if (dfs(nodeId)) {
        return true;
      }
    }
  }

  return false;
}

/**
 * Check if all node references in edges exist
 */
function validateNodeReferences(nodes, edges) {
  const nodeIds = new Set(nodes.map(n => n.id));
  const errors = [];

  edges.forEach((edge, index) => {
    if (!nodeIds.has(edge.source)) {
      errors.push(`Edge ${index}: source node '${edge.source}' does not exist`);
    }
    if (!nodeIds.has(edge.target)) {
      errors.push(`Edge ${index}: target node '${edge.target}' does not exist`);
    }
  });

  return errors;
}

/**
 * Check for duplicate node IDs
 */
function validateUniqueNodeIds(nodes) {
  const ids = nodes.map(n => n.id);
  const duplicates = ids.filter((id, index) => ids.indexOf(id) !== index);

  if (duplicates.length > 0) {
    return [`Duplicate node IDs found: ${[...new Set(duplicates)].join(', ')}`];
  }

  return [];
}

/**
 * Validate node parameters
 * TODO: Add schema-based validation when MCP tool schemas are available
 */
function validateNodeParameters(nodes) {
  const errors = [];

  nodes.forEach(node => {
    if (!node.data) {
      errors.push(`Node ${node.id}: missing data`);
      return;
    }

    if (!node.data.mcp_server) {
      errors.push(`Node ${node.id}: missing mcp_server`);
    }

    if (!node.data.tool) {
      errors.push(`Node ${node.id}: missing tool`);
    }

    // Check params exist (even if empty object)
    if (!node.data.params) {
      errors.push(`Node ${node.id}: missing params`);
    }
  });

  return errors;
}

/**
 * Check for disconnected nodes (nodes with no connections)
 * This is a warning, not an error
 */
function findDisconnectedNodes(nodes, edges) {
  const connectedIds = new Set();

  edges.forEach(edge => {
    connectedIds.add(edge.source);
    connectedIds.add(edge.target);
  });

  const disconnected = nodes
    .filter(node => !connectedIds.has(node.id))
    .map(node => node.id);

  return disconnected;
}

/**
 * Validate entire workflow
 * Returns { valid: boolean, errors: string[], warnings: string[] }
 */
export function validateWorkflow(nodes, edges) {
  const errors = [];
  const warnings = [];

  // Check for empty workflow
  if (nodes.length === 0) {
    errors.push('Workflow is empty - add at least one node');
    return { valid: false, errors, warnings };
  }

  // Check for cycles
  if (hasCycles(nodes, edges)) {
    errors.push('Workflow contains cycles - circular dependencies are not allowed');
  }

  // Check node references
  const refErrors = validateNodeReferences(nodes, edges);
  errors.push(...refErrors);

  // Check unique node IDs
  const idErrors = validateUniqueNodeIds(nodes);
  errors.push(...idErrors);

  // Check node parameters
  const paramErrors = validateNodeParameters(nodes);
  errors.push(...paramErrors);

  // Check for disconnected nodes (warning only)
  const disconnected = findDisconnectedNodes(nodes, edges);
  if (disconnected.length > 0) {
    warnings.push(`Disconnected nodes found: ${disconnected.join(', ')}`);
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

/**
 * Check if workflow is executable (has at least one node, no critical errors)
 */
export function canExecuteWorkflow(nodes, edges) {
  if (nodes.length === 0) {
    return { can: false, reason: 'Workflow is empty' };
  }

  const validation = validateWorkflow(nodes, edges);
  if (!validation.valid) {
    return { can: false, reason: validation.errors[0] };
  }

  return { can: true, reason: null };
}
