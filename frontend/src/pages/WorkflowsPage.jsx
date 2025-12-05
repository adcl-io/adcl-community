/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React, { useState, useCallback } from 'react';
import { Zap, AlertCircle, AlertTriangle, Play, Loader2 } from 'lucide-react';
import { ReactFlowProvider } from 'reactflow';
import axios from 'axios';

// Custom hooks
import useWorkflow from '../hooks/useWorkflow';
import useExecution from '../hooks/useExecution';
import useMCPRegistry from '../hooks/useMCPRegistry';

// Components
import WorkflowCanvas from '../components/workflow/WorkflowCanvas';
import NodePalette from '../components/workflow/NodePalette';
import ResultsViewer from '../components/workflow/ResultsViewer';
import WorkflowToolbar from '../components/workflow/WorkflowToolbar';
import NodeConfigModal from '../components/workflow/NodeConfigModal';
import ErrorBoundary from '../components/ErrorBoundary';
import { Button } from '@/components/ui/button';

// Utils
import { validateWorkflow, canExecuteWorkflow } from '../utils/workflowValidation';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Workflows Page - Main Component
 * Orchestrates workflow editing and execution
 */
function WorkflowsPage() {
  // Custom hooks
  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    resetNodeStates,
    updateNodeState,
    loadExampleWorkflow,
    addNode,
    updateNodeParams,
    saveWorkflow,
    loadWorkflow,
    listWorkflows,
    deleteWorkflow,
  } = useWorkflow();

  const { servers, loading, error } = useMCPRegistry();
  const { executing, result, executeWorkflow } = useExecution();

  // Workflow name state
  const [workflowName, setWorkflowName] = useState('Untitled Workflow');

  // Validation state
  const [validationErrors, setValidationErrors] = useState([]);
  const [validationWarnings, setValidationWarnings] = useState([]);

  // Node configuration modal state
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [toolSchema, setToolSchema] = useState(null);

  // Handle workflow execution
  const handleExecute = () => {
    // Validate workflow before execution
    const validation = validateWorkflow(nodes, edges);

    if (!validation.valid) {
      setValidationErrors(validation.errors);
      setValidationWarnings(validation.warnings);
      return;
    }

    // Clear any previous validation errors
    setValidationErrors([]);
    setValidationWarnings(validation.warnings);

    // Execute workflow
    resetNodeStates();
    executeWorkflow(nodes, edges, updateNodeState);
  };

  // Handle node double-click to open config modal
  const handleNodeDoubleClick = useCallback(async (nodeId, nodeData) => {
    const node = nodes.find(n => n.id === nodeId);
    if (!node) return;

    setSelectedNode(node);
    
    // Fetch tool schema
    try {
      const response = await axios.get(
        `${API_URL}/mcp/servers/${nodeData.mcp_server}/tools`
      );
      const tool = response.data.tools.find(t => t.name === nodeData.tool);
      setToolSchema(tool);
      setConfigModalOpen(true);
    } catch (error) {
      console.error('Failed to fetch tool schema:', error);
    }
  }, [nodes]);

  // Handle saving node parameters
  const handleSaveNodeParams = useCallback((nodeId, params) => {
    updateNodeParams(nodeId, params);
  }, [updateNodeParams]);

  // Add double-click handler to all nodes
  const nodesWithHandlers = nodes.map(node => ({
    ...node,
    data: {
      ...node.data,
      onNodeDoubleClick: handleNodeDoubleClick,
    },
  }));

  return (
    <ReactFlowProvider>
      <div className="flex h-screen w-full overflow-hidden">
        <div className="w-[350px] bg-card text-foreground p-5 overflow-y-auto flex flex-col gap-5 flex-shrink-0 border-r border-border">
          <div className="flex items-center justify-between mb-0">
            <h1 className="text-xl font-semibold flex items-center gap-2">
              <Zap className="h-5 w-5" />
              Workflow Builder
            </h1>
            <Button
              onClick={handleExecute}
              disabled={nodes.length === 0 || executing}
              size="sm"
              className="h-8 w-8 p-0"
            >
              {executing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
            </Button>
          </div>

          <NodePalette servers={servers} loading={loading} error={error} />

          <WorkflowToolbar 
            onSave={saveWorkflow}
            onLoad={loadWorkflow}
            onListWorkflows={listWorkflows}
            onDeleteWorkflow={deleteWorkflow}
            workflowName={workflowName}
            onWorkflowNameChange={setWorkflowName}
          />

          {/* Validation Errors */}
          {validationErrors.length > 0 && (
            <div className="border-t border-border pt-4">
              <div className="bg-destructive/10 border-l-4 border-l-destructive p-3 rounded">
                <h3 className="text-sm font-bold mb-2 flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  Validation Errors
                </h3>
                <ul className="list-disc pl-5 text-sm space-y-1">
                  {validationErrors.map((err, i) => (
                    <li key={i} className="text-destructive">{err}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Validation Warnings */}
          {validationWarnings.length > 0 && (
            <div className="border-t border-border pt-4">
              <div className="bg-yellow-500/10 border-l-4 border-l-yellow-500 p-3 rounded">
                <h3 className="text-sm font-bold mb-2 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  Warnings
                </h3>
                <ul className="list-disc pl-5 text-sm space-y-1">
                  {validationWarnings.map((warn, i) => (
                    <li key={i} className="text-yellow-600 dark:text-yellow-500">{warn}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          <ResultsViewer result={result} />
        </div>

        <WorkflowCanvas
          nodes={nodesWithHandlers}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onAddNode={addNode}
        />

        <NodeConfigModal
          node={selectedNode}
          toolSchema={toolSchema}
          open={configModalOpen}
          onClose={() => setConfigModalOpen(false)}
          onSave={handleSaveNodeParams}
        />
      </div>
    </ReactFlowProvider>
  );
}

// Wrap WorkflowsPage with ErrorBoundary
export default function WorkflowsPageWithErrorBoundary() {
  return (
    <ErrorBoundary>
      <WorkflowsPage />
    </ErrorBoundary>
  );
}
