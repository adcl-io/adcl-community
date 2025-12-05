/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React, { useRef, useCallback } from 'react';
import ReactFlow, { Background, Controls, MiniMap, useReactFlow } from 'reactflow';
import 'reactflow/dist/style.css';
import MCPNode from './MCPNode';

const nodeTypes = {
  mcpNode: MCPNode,
};

/**
 * Workflow Canvas Component
 * Wraps ReactFlow for visual workflow editing with drag-and-drop support
 */
function WorkflowCanvas({ nodes, edges, onNodesChange, onEdgesChange, onConnect, onAddNode }) {
  const reactFlowWrapper = useRef(null);
  const { project } = useReactFlow();

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const data = event.dataTransfer.getData('application/reactflow');

      if (!data) return;

      const { mcpServer, tool } = JSON.parse(data);

      // Calculate position relative to the ReactFlow canvas
      const position = project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      // Call the addNode function passed from parent
      if (onAddNode) {
        onAddNode(mcpServer, tool, position);
      }
    },
    [project, onAddNode]
  );

  return (
    <div 
      ref={reactFlowWrapper}
      className="flex-1 bg-background min-h-0 h-full w-full relative"
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        onDrop={onDrop}
        onDragOver={onDragOver}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}

export default WorkflowCanvas;
