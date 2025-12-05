/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React, { useState, useCallback, useEffect } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import axios from 'axios';
import './App.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Custom Node Component with execution state
function MCPNode({ data }) {
  const status = data.executionStatus || 'idle';
  const statusIcons = {
    idle: '',
    pending: '⏸️',
    running: '⚙️',
    completed: '✅',
    error: '❌'
  };

  return (
    <div className={`mcp-node mcp-node-${status}`}>
      <div className="node-header">
        <strong>{data.label}</strong>
        {statusIcons[status] && <span className="status-icon">{statusIcons[status]}</span>}
      </div>
      <div className="node-body">
        <div className="node-field">
          <span>Server:</span> <code>{data.mcp_server}</code>
        </div>
        <div className="node-field">
          <span>Tool:</span> <code>{data.tool}</code>
        </div>
        {status !== 'idle' && (
          <div className="node-status">
            <small>{status.toUpperCase()}</small>
          </div>
        )}
      </div>
    </div>
  );
}

// Nmap Result Renderer
function NmapResultRenderer({ data }) {
  if (!data) return null;

  // Check if this looks like nmap data
  if (data.ports || data.services || data.vulnerabilities || data.summary) {
    return (
      <div className="nmap-results">
        <h3>🔍 Network Scan Results</h3>

        {data.target && (
          <div className="nmap-section">
            <strong>Target:</strong> <code>{data.target}</code>
          </div>
        )}

        {data.summary && data.summary.open_ports !== undefined && (
          <div className="nmap-section">
            <strong>Summary:</strong>
            <div className="nmap-stats">
              <span className="stat">Open Ports: {data.summary.open_ports}</span>
              {data.summary.open_port_list && (
                <div className="port-list">
                  {data.summary.open_port_list.map((port, i) => (
                    <span key={i} className="port-badge">{port}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {data.services && data.services.length > 0 && (
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
                {data.services.map((svc, i) => {
                  // Handle service being either a string or object
                  const serviceName = typeof svc.service === 'object'
                    ? svc.service.name
                    : svc.service;

                  // Get version from service object or top level
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
        )}

        {data.vulnerabilities && data.vulnerabilities.length > 0 && (
          <div className="nmap-section vulnerability-section">
            <strong>⚠️ Vulnerabilities Found:</strong>
            {data.vulnerabilities.map((vuln, i) => (
              <div key={i} className="vulnerability-item">
                <div><strong>Port {vuln.port}:</strong> {vuln.script}</div>
                <div className="vuln-finding">{vuln.finding}</div>
              </div>
            ))}
          </div>
        )}

        {data.os_matches && data.os_matches.length > 0 && (
          <div className="nmap-section">
            <strong>OS Detection:</strong>
            <ul className="os-list">
              {data.os_matches.slice(0, 3).map((os, i) => (
                <li key={i}>
                  {os.name} <span className="accuracy">({os.accuracy}% accuracy)</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  return null;
}

// Smart Result Renderer
function ResultRenderer({ nodeId, data }) {
  try {
    // Handle null/undefined data
    if (!data) {
      return (
        <details>
          <summary>📄 {nodeId} (no data)</summary>
          <p>No result data available</p>
        </details>
      );
    }

    // Check if this is nmap data
    const nmapResult = NmapResultRenderer({ data });
    if (nmapResult) return nmapResult;

    // Check if it's agent reasoning
    if (data && data.reasoning) {
      // Ensure reasoning is a string and handle it safely
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

    // Check if it's code
    if (data && data.code) {
      return (
        <div className="code-result">
          <h4>💻 Generated Code</h4>
          <pre><code>{data.code}</code></pre>
        </div>
      );
    }

    // Check if it's a file write result (simple success message)
    if (data && typeof data === 'object' && Object.keys(data).length < 5) {
      return (
        <details>
          <summary>📄 {nodeId}</summary>
          <pre>{JSON.stringify(data, null, 2)}</pre>
        </details>
      );
    }

    // Truncate very large results
    const jsonStr = JSON.stringify(data, null, 2);
    if (jsonStr && jsonStr.length > 10000) {
      return (
        <details>
          <summary>📄 {nodeId} (large result - {(jsonStr.length / 1024).toFixed(1)}KB)</summary>
          <pre>{jsonStr.substring(0, 10000) + '\n\n... (truncated)'}</pre>
        </details>
      );
    }

    // Default JSON view
    return (
      <details>
        <summary>📄 {nodeId}</summary>
        <pre>{jsonStr}</pre>
      </details>
    );
  } catch (error) {
    console.error('Error rendering result for', nodeId, error);
    return (
      <div className="agent-result">
        <h4>⚠️ Rendering Error for {nodeId}</h4>
        <p>Could not render result: {error.message}</p>
        <details>
          <summary>Raw data</summary>
          <pre>{String(data)}</pre>
        </details>
      </div>
    );
  }
}

// Console Log Component
function ConsoleLog({ logs }) {
  const logRef = React.useRef(null);

  // Auto-scroll to bottom on new logs
  React.useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs]);

  if (!logs || logs.length === 0) return null;

  return (
    <div className="console-container">
      <h2>📟 Execution Console</h2>
      <div className="console-log" ref={logRef}>
        {logs.map((log, index) => (
          <div key={index} className={`console-entry console-${log.level}`}>
            <span className="console-time">{new Date(log.timestamp).toLocaleTimeString()}</span>
            <span className="console-message">{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const nodeTypes = {
  mcpNode: MCPNode,
};

// Error Boundary Component
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('React Error Boundary caught an error:', error, errorInfo);
    this.setState({ error, errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '20px', background: '#2d2d2d', color: '#fff', minHeight: '100vh' }}>
          <h1 style={{ color: '#ea4335' }}>⚠️ Something went wrong</h1>
          <details style={{ marginTop: '20px', cursor: 'pointer' }}>
            <summary style={{ color: '#8ab4f8', fontSize: '16px' }}>Error Details</summary>
            <div style={{ marginTop: '10px', padding: '10px', background: '#1e1e1e', borderRadius: '4px' }}>
              <h3>Error:</h3>
              <pre style={{ color: '#ea4335', whiteSpace: 'pre-wrap' }}>
                {this.state.error && this.state.error.toString()}
              </pre>
              {this.state.errorInfo && (
                <>
                  <h3>Component Stack:</h3>
                  <pre style={{ color: '#fbbc04', whiteSpace: 'pre-wrap', fontSize: '12px' }}>
                    {this.state.errorInfo.componentStack}
                  </pre>
                </>
              )}
            </div>
          </details>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: '20px',
              padding: '10px 20px',
              background: '#8ab4f8',
              color: '#1e1e1e',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: 'bold'
            }}
          >
            Reload Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [servers, setServers] = useState([]);
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState(null);

  // Load MCP servers
  useEffect(() => {
    loadServers();
  }, []);

  const loadServers = async () => {
    try {
      const response = await axios.get(`${API_URL}/mcp/servers`);
      setServers(response.data);
    } catch (error) {
      console.error('Failed to load servers:', error);
    }
  };

  // Load example workflow
  const loadExampleWorkflow = async (filename = 'hello_world.json') => {
    try {
      const response = await axios.get(`${API_URL}/workflows/examples/${filename}`);
      const workflow = response.data;

      // Convert workflow to React Flow format
      const flowNodes = workflow.nodes.map((node, index) => ({
        id: node.id,
        type: 'mcpNode',
        position: { x: 100 + index * 250, y: 100 },
        data: {
          label: `${node.mcp_server}.${node.tool}`,
          mcp_server: node.mcp_server,
          tool: node.tool,
          params: node.params,
        },
      }));

      const flowEdges = workflow.edges.map((edge, index) => ({
        id: `edge-${index}`,
        source: edge.source,
        target: edge.target,
        animated: true,
      }));

      setNodes(flowNodes);
      setEdges(flowEdges);
    } catch (error) {
      console.error('Failed to load example:', error);
    }
  };

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const executeWorkflow = async () => {
    setExecuting(true);
    setResult(null);

    // Reset all nodes to idle state
    setNodes((nds) =>
      nds.map((node) => ({
        ...node,
        data: { ...node.data, executionStatus: 'idle' },
      }))
    );

    // Generate session ID
    const sessionId = `session-${Date.now()}`;

    // Connect to WebSocket
    const wsUrl = API_URL.replace('http', 'ws');
    const ws = new WebSocket(`${wsUrl}/ws/execute/${sessionId}`);

    const logs = [];
    let finalResult = null;

    ws.onopen = () => {
      console.log('WebSocket connected');

      // Convert React Flow format back to workflow format
      const workflow = {
        name: 'Interactive Workflow',
        nodes: nodes.map((node) => ({
          id: node.id,
          type: 'mcp_call',
          mcp_server: node.data.mcp_server,
          tool: node.data.tool,
          params: node.data.params || {},
        })),
        edges: edges.map((edge) => ({
          source: edge.source,
          target: edge.target,
        })),
      };

      // Send workflow to execute
      ws.send(JSON.stringify({ workflow }));
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);

        if (message.type === 'log') {
          // Add log to list
          logs.push(message.log);

          // Update result with current logs and node states
          setResult({
            status: 'running',
            results: {},
            errors: [],
            logs: [...logs],
            node_states: message.node_states || {}
          });
        } else if (message.type === 'node_state') {
          // Update specific node state in real-time
          setNodes((nds) =>
            nds.map((node) =>
              node.id === message.node_id
                ? {
                    ...node,
                    data: {
                      ...node.data,
                      executionStatus: message.status,
                    },
                  }
                : node
            )
          );

          // Update all node states
          if (message.node_states) {
            setNodes((nds) =>
              nds.map((node) => ({
                ...node,
                data: {
                  ...node.data,
                  executionStatus: message.node_states[node.id] || node.data.executionStatus,
                },
              }))
            );
          }
        } else if (message.type === 'complete') {
          // Execution complete
          console.log('Execution complete, result:', message.result);
          finalResult = message.result;

          // Log each result for debugging
          if (finalResult.results) {
            Object.entries(finalResult.results).forEach(([nodeId, data]) => {
              console.log(`Result for ${nodeId}:`, typeof data, data);
            });
          }

          setResult(finalResult);
          setExecuting(false);
          ws.close();
        } else if (message.type === 'error') {
          // Error occurred
          console.error('Execution error:', message.error);
          setResult({
            status: 'error',
            results: {},
            errors: [message.error],
            logs: logs,
            node_states: {}
          });
          setExecuting(false);
          ws.close();
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error, event.data);
        setResult({
          status: 'error',
          results: {},
          errors: ['Failed to parse execution update'],
          logs: logs,
          node_states: {}
        });
        setExecuting(false);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setResult({
        status: 'error',
        errors: ['WebSocket connection error'],
        logs: logs
      });
      setExecuting(false);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
      if (finalResult) {
        // Update final node states
        setNodes((nds) =>
          nds.map((node) => ({
            ...node,
            data: {
              ...node.data,
              executionStatus: finalResult.node_states[node.id] || 'idle',
            },
          }))
        );
      }
    };
  };

  return (
    <div className="app">
      <div className="sidebar">
        <h1>MCP Agent Platform</h1>

        <div className="section">
          <h2>MCP Servers</h2>
          <div className="server-list">
            {servers.map((server) => (
              <div key={server.name} className="server-item">
                <strong>{server.name}</strong>
                <small>{server.description}</small>
              </div>
            ))}
          </div>
        </div>

        <div className="section">
          <h2>Example Workflows</h2>
          <div className="workflow-buttons">
            <button onClick={() => loadExampleWorkflow('hello_world.json')} className="btn btn-sm">
              Hello World
            </button>
            <button onClick={() => loadExampleWorkflow('code_review.json')} className="btn btn-sm">
              Code Review
            </button>
            <button onClick={() => loadExampleWorkflow('nmap_recon.json')} className="btn btn-sm">
              🔍 Nmap Recon
            </button>
            <button onClick={() => loadExampleWorkflow('full_recon.json')} className="btn btn-sm">
              🛡️ Full Security Scan
            </button>
          </div>
        </div>

        <div className="section">
          <h2>Actions</h2>
          <button
            onClick={executeWorkflow}
            disabled={executing || nodes.length === 0}
            className="btn btn-primary"
          >
            {executing ? 'Executing...' : 'Execute Workflow'}
          </button>
        </div>

        {result && result.logs && result.logs.length > 0 && (
          <div className="section">
            <ConsoleLog logs={result.logs} />
          </div>
        )}

        {result && (
          <div className="section">
            <h2>Results</h2>
            <div className={`result ${result.status}`}>
              <strong>Status:</strong> {result.status}
              {result.errors && result.errors.length > 0 && (
                <div className="errors">
                  <strong>Errors:</strong>
                  <ul>
                    {result.errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
              {result.results && (
                <div className="results-container">
                  {Object.entries(result.results).map(([nodeId, data]) => {
                    try {
                      return <ResultRenderer key={nodeId} nodeId={nodeId} data={data} />;
                    } catch (error) {
                      console.error(`Error rendering result for ${nodeId}:`, error);
                      return (
                        <div key={nodeId} className="agent-result">
                          <h4>⚠️ Rendering Error for {nodeId}</h4>
                          <p>Failed to render result: {error.message}</p>
                        </div>
                      );
                    }
                  })}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
        >
          <Background />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </div>
    </div>
  );
}

// Wrap App with ErrorBoundary
function AppWithErrorBoundary() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}

export default AppWithErrorBoundary;
