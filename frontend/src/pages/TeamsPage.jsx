/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Users,
  Plus,
  Play,
  Edit,
  Download,
  Trash2,
  Loader2,
  FileCode,
  RefreshCw,
  Shield,
  Code,
  TestTube,
  Rocket as RocketIcon,
  Activity
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function TeamsPage() {
  const [teams, setTeams] = useState([]);
  const [mcpServers, setMcpServers] = useState([]);
  const [availableAgents, setAvailableAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showRunModal, setShowRunModal] = useState(false);
  const [editingTeam, setEditingTeam] = useState(null);
  const [runningTeam, setRunningTeam] = useState(null);
  const [teamTask, setTeamTask] = useState('');
  const [teamResult, setTeamResult] = useState(null);
  const [executingTeam, setExecutingTeam] = useState(false);
  const [progressLog, setProgressLog] = useState([]);
  const [executionId, setExecutionId] = useState(null);

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    version: '1.0.0',
    available_mcps: [],
    agents: [],
    coordination: {
      mode: 'sequential',
      share_context: true
    },
    tags: []
  });

  useEffect(() => {
    loadTeams();
    loadMcpServers();
    loadAvailableAgents();
  }, []);

  const migrateTeamFormat = (team) => {
    // Migrate old team format to new format
    const migratedTeam = { ...team };

    if (migratedTeam.agents) {
      migratedTeam.agents = migratedTeam.agents.map(agent => {
        const migratedAgent = { ...agent };

        // Migrate 'name' to 'agent_id'
        if (agent.name && !agent.agent_id) {
          migratedAgent.agent_id = agent.name.toLowerCase().replace(/\s+/g, '-');
          delete migratedAgent.name;
        }

        // Migrate 'mcp_server' (string) to 'mcp_access' (array)
        if (agent.mcp_server && !agent.mcp_access) {
          migratedAgent.mcp_access = [agent.mcp_server];
          delete migratedAgent.mcp_server;
        }

        // Ensure required fields exist
        if (!migratedAgent.responsibilities) migratedAgent.responsibilities = [];
        if (!migratedAgent.mcp_access) migratedAgent.mcp_access = [];

        return migratedAgent;
      });
    }

    // Ensure team-level fields exist
    if (!migratedTeam.available_mcps) migratedTeam.available_mcps = [];
    if (!migratedTeam.coordination) {
      migratedTeam.coordination = { mode: 'sequential', share_context: true };
    }
    if (!migratedTeam.tags) migratedTeam.tags = [];

    return migratedTeam;
  };

  const loadTeams = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/teams`);
      // Migrate any old format teams
      const migratedTeams = response.data.map(migrateTeamFormat);
      setTeams(migratedTeams);
    } catch (error) {
      console.error('Failed to load teams:', error);
      setTeams([]);
    } finally {
      setLoading(false);
    }
  };

  const loadMcpServers = async () => {
    try {
      const response = await axios.get(`${API_URL}/mcp/servers`);
      setMcpServers(response.data);
    } catch (error) {
      console.error('Failed to load MCP servers:', error);
      setMcpServers([]);
    }
  };

  const loadAvailableAgents = async () => {
    try {
      const response = await axios.get(`${API_URL}/agents`);
      setAvailableAgents(response.data);
    } catch (error) {
      console.error('Failed to load agents:', error);
      setAvailableAgents([]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validate required fields
    if (!formData.available_mcps || formData.available_mcps.length === 0) {
      alert('Please select at least one MCP tool for the team pool');
      return;
    }

    if (!formData.agents || formData.agents.length === 0) {
      alert('Please add at least one agent to the team');
      return;
    }

    // Validate each agent has required fields
    for (let i = 0; i < formData.agents.length; i++) {
      const agent = formData.agents[i];
      if (!agent.agent_id) {
        alert(`Agent ${i + 1}: Please select an agent ID`);
        return;
      }
      if (!agent.role || agent.role.trim() === '') {
        alert(`Agent ${i + 1}: Please enter a role for this agent`);
        return;
      }
    }

    const teamId = formData.name.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
    const teamData = {
      ...formData,
      id: editingTeam?.id || teamId,
      author: "User"
    };

    try {
      if (editingTeam) {
        await axios.put(`${API_URL}/teams/${editingTeam.id}`, teamData);
      } else {
        await axios.post(`${API_URL}/teams`, teamData);
      }
      loadTeams();
      resetForm();
    } catch (error) {
      console.error('Failed to save team:', error);
      const errorDetail = error.response?.data?.detail;
      let errorMessage;

      if (typeof errorDetail === 'string') {
        errorMessage = errorDetail;
      } else if (Array.isArray(errorDetail)) {
        // Pydantic validation errors - show field names
        errorMessage = errorDetail.map(e => {
          const field = e.loc?.join('.') || 'unknown field';
          const msg = e.msg || e;
          return `${field}: ${msg}`;
        }).join('; ');
      } else {
        errorMessage = JSON.stringify(errorDetail) || error.message;
      }

      alert('Failed to save team: ' + errorMessage);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this team? This will remove the team file from disk.')) return;

    try {
      await axios.delete(`${API_URL}/teams/${id}`);
      loadTeams();
    } catch (error) {
      console.error('Failed to delete team:', error);
      const errorDetail = error.response?.data?.detail;
      let errorMessage;

      if (typeof errorDetail === 'string') {
        errorMessage = errorDetail;
      } else if (Array.isArray(errorDetail)) {
        errorMessage = errorDetail.map(e => {
          const field = e.loc?.join('.') || 'unknown field';
          const msg = e.msg || e;
          return `${field}: ${msg}`;
        }).join('; ');
      } else {
        errorMessage = JSON.stringify(errorDetail) || error.message;
      }

      alert('Failed to delete team: ' + errorMessage);
    }
  };

  const exportTeam = async (id) => {
    try {
      const response = await axios.post(`${API_URL}/teams/${id}/export`);
      const teamData = response.data;

      const blob = new Blob([JSON.stringify(teamData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${id}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export team:', error);
      const errorDetail = error.response?.data?.detail;
      let errorMessage;

      if (typeof errorDetail === 'string') {
        errorMessage = errorDetail;
      } else if (Array.isArray(errorDetail)) {
        errorMessage = errorDetail.map(e => {
          const field = e.loc?.join('.') || 'unknown field';
          const msg = e.msg || e;
          return `${field}: ${msg}`;
        }).join('; ');
      } else {
        errorMessage = JSON.stringify(errorDetail) || error.message;
      }

      alert('Failed to export team: ' + errorMessage);
    }
  };

  const runTeam = async () => {
    if (!runningTeam || !teamTask.trim()) return;

    try {
      setExecutingTeam(true);
      setTeamResult(null);
      setProgressLog([]);
      setExecutionId(null);

      // Use SSE streaming for real-time progress updates
      const eventSourceUrl = `${API_URL}/teams/run/stream?team_id=${encodeURIComponent(runningTeam.id)}&task=${encodeURIComponent(teamTask)}`;

      // For SSE, we need to use fetch with POST, then handle the stream
      const response = await fetch(`${API_URL}/teams/run/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          team_id: runningTeam.id,
          task: teamTask,
          context: {}
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      // Read SSE stream
      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            console.log('SSE event:', data);

            switch (data.type) {
              case 'execution_started':
                setExecutionId(data.execution_id);
                setProgressLog(prev => [...prev, `🚀 Execution started (ID: ${data.execution_id})`]);
                break;

              case 'agent_start':
                setProgressLog(prev => [...prev, `🤖 Starting ${data.role} (${data.agent_id})...`]);
                break;

              case 'agent_iteration':
                // Build detailed iteration log entry
                let logEntry = `  ⚡ Iteration ${data.iteration}/${data.max_iterations}`;

                if (data.token_usage) {
                  logEntry += ` • ${data.token_usage.input_tokens} in / ${data.token_usage.output_tokens} out`;
                }

                if (data.model) {
                  logEntry += ` • ${data.model}`;
                }

                // Note: Individual tool executions are now shown via tool_execution events
                // This keeps the iteration summary concise

                setProgressLog(prev => [...prev, logEntry]);

                // Add thinking preview if available
                if (data.thinking_preview) {
                  // Only add ellipsis if the thinking was truncated
                  const thinkingText = data.thinking_preview.length >= 499
                    ? `${data.thinking_preview}...`
                    : data.thinking_preview;
                  setProgressLog(prev => [...prev, `     💭 ${thinkingText}`]);
                }
                break;

              case 'tool_execution':
                // Real-time update for individual tool calls
                setProgressLog(prev => [...prev, `     🔧 ${data.tool_summary}`]);
                break;

              case 'agent_complete':
                setProgressLog(prev => [...prev, `✅ ${data.role} completed (${data.status})`]);
                break;

              case 'complete':
                setTeamResult(data.result);
                setProgressLog(prev => [...prev, `✨ Team execution completed!`]);
                setExecutingTeam(false);
                break;

              case 'error':
                setTeamResult({
                  status: 'error',
                  error: data.message
                });
                setProgressLog(prev => [...prev, `❌ Error: ${data.message}`]);
                setExecutingTeam(false);
                break;
            }
          }
        }
      }

    } catch (error) {
      console.error('Error running team:', error);
      setTeamResult({
        status: 'error',
        error: error.message
      });
      setProgressLog(prev => [...prev, `❌ Error: ${error.message}`]);
      setExecutingTeam(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      version: '1.0.0',
      available_mcps: [],
      agents: [],
      coordination: {
        mode: 'sequential',
        share_context: true
      },
      tags: []
    });
    setEditingTeam(null);
    setShowModal(false);
  };

  const startEdit = (team) => {
    // Migrate team format if needed
    const migratedTeam = migrateTeamFormat(team);

    setEditingTeam(migratedTeam);
    setFormData({
      name: migratedTeam.name,
      description: migratedTeam.description || '',
      version: migratedTeam.version || '1.0.0',
      available_mcps: migratedTeam.available_mcps || [],
      agents: migratedTeam.agents || [],
      coordination: migratedTeam.coordination || { mode: 'sequential', share_context: true },
      tags: migratedTeam.tags || []
    });
    setShowModal(true);
  };

  const startRun = (team) => {
    setRunningTeam(team);
    setTeamTask('');
    setTeamResult(null);
    setShowRunModal(true);
  };

  const toggleMcp = (mcpName) => {
    const currentMcps = formData.available_mcps || [];
    if (currentMcps.includes(mcpName)) {
      setFormData({
        ...formData,
        available_mcps: currentMcps.filter(m => m !== mcpName)
      });
    } else {
      setFormData({
        ...formData,
        available_mcps: [...currentMcps, mcpName]
      });
    }
  };

  const addAgent = () => {
    setFormData({
      ...formData,
      agents: [
        ...formData.agents,
        {
          agent_id: availableAgents[0]?.id || '',
          role: '',
          responsibilities: [],
          mcp_access: []
        }
      ]
    });
  };

  const updateAgent = (index, field, value) => {
    const newAgents = [...formData.agents];
    newAgents[index][field] = value;
    setFormData({ ...formData, agents: newAgents });
  };

  const toggleAgentMcp = (agentIndex, mcpName) => {
    const newAgents = [...formData.agents];
    const currentMcps = newAgents[agentIndex].mcp_access || [];

    if (currentMcps.includes(mcpName)) {
      newAgents[agentIndex].mcp_access = currentMcps.filter(m => m !== mcpName);
    } else {
      newAgents[agentIndex].mcp_access = [...currentMcps, mcpName];
    }

    setFormData({ ...formData, agents: newAgents });
  };

  const removeAgent = (index) => {
    const newAgents = formData.agents.filter((_, i) => i !== index);
    setFormData({ ...formData, agents: newAgents });
  };

  const getAgentIcon = (role) => {
    const roleLower = role?.toLowerCase() || '';
    if (roleLower.includes('security') || roleLower.includes('scan')) return Shield;
    if (roleLower.includes('code') || roleLower.includes('review')) return Code;
    if (roleLower.includes('test')) return TestTube;
    if (roleLower.includes('deploy')) return RocketIcon;
    if (roleLower.includes('monitor')) return Activity;
    return Users;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-foreground flex items-center gap-2">
              <Users className="h-8 w-8" />
              Multi-Agent Teams
            </h1>
            <p className="text-muted-foreground mt-1">Teams of autonomous agents with shared MCP tool pools</p>
          </div>
          <Button onClick={() => setShowModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create Team
          </Button>
        </div>

        {teams.length === 0 ? (
          <Card className="p-12">
            <div className="text-center">
              <Users className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-xl font-semibold text-foreground mb-2">No Teams Yet</h3>
              <p className="text-muted-foreground mb-6">Create your first multi-agent team to enable autonomous agents to collaborate.</p>
              <Button onClick={() => setShowModal(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Your First Team
              </Button>
            </div>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {teams.map(team => {
              const AgentIcon = getAgentIcon(team.agents?.[0]?.role);
              return (
                <Card key={team.id} className="hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <Users className="h-5 w-5 text-primary" />
                        <CardTitle className="text-lg">{team.name}</CardTitle>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground mt-2">
                      <Badge variant="secondary">
                        {team.agents?.length || 0} agent{team.agents?.length !== 1 ? 's' : ''}
                      </Badge>
                      <Badge variant="secondary">
                        {team.available_mcps?.length || 0} MCP{team.available_mcps?.length !== 1 ? 's' : ''}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex gap-2 text-xs">
                      <Badge variant="outline">
                        <FileCode className="h-3 w-3 mr-1" />
                        {team.file || `${team.id}.json`}
                      </Badge>
                      <Badge variant="outline">v{team.version || '1.0.0'}</Badge>
                      <Badge variant="outline">
                        <RefreshCw className="h-3 w-3 mr-1" />
                        {team.coordination?.mode || 'sequential'}
                      </Badge>
                    </div>

                    {team.description && (
                      <p className="text-sm text-muted-foreground">{team.description}</p>
                    )}

                    {team.available_mcps && team.available_mcps.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-foreground mb-2 flex items-center gap-1">
                          <FileCode className="h-3 w-3" />
                          MCP Tool Pool
                        </h4>
                        <div className="flex flex-wrap gap-1">
                          {team.available_mcps.map((mcp, index) => (
                            <Badge key={index} variant="secondary" className="text-xs">
                              {mcp}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {team.agents && team.agents.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-foreground mb-2">Team Members</h4>
                        <div className="space-y-2">
                          {team.agents.map((agent, index) => {
                            const Icon = getAgentIcon(agent.role);
                            return (
                              <div key={index} className="flex items-start gap-2 p-2 bg-background rounded-md text-xs">
                                <Icon className="h-4 w-4 mt-0.5 text-primary" />
                                <div className="flex-1 min-w-0">
                                  <div className="font-medium">{agent.role || agent.agent_id}</div>
                                  <code className="text-xs text-muted-foreground">{agent.agent_id}</code>
                                  {agent.mcp_access && agent.mcp_access.length > 0 && (
                                    <div className="text-xs text-muted-foreground mt-1">
                                      Restricted: {agent.mcp_access.join(', ')}
                                    </div>
                                  )}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    <div className="flex flex-wrap gap-2 pt-2">
                      <Button size="sm" onClick={() => startRun(team)}>
                        <Play className="h-3 w-3 mr-1" />
                        Run
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => startEdit(team)}>
                        <Edit className="h-3 w-3 mr-1" />
                        Edit
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => exportTeam(team.id)}>
                        <Download className="h-3 w-3 mr-1" />
                        Export
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => handleDelete(team.id)}>
                        <Trash2 className="h-3 w-3 mr-1" />
                        Delete
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* Create/Edit Team Modal */}
        <Dialog open={showModal} onOpenChange={(open) => !open && resetForm()}>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{editingTeam ? 'Edit Team' : 'Create New Team'}</DialogTitle>
              <DialogDescription>
                Configure a multi-agent team with shared MCP tools
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="name">Team Name</Label>
                <Input
                  id="name"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Security Assessment Team"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="What does this team do?"
                  rows={3}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="version">Version</Label>
                  <Input
                    id="version"
                    value={formData.version}
                    onChange={(e) => setFormData({ ...formData, version: e.target.value })}
                    placeholder="e.g., 1.0.0"
                    pattern="^\d+\.\d+\.\d+$"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="coordination">Coordination Mode</Label>
                  <Select
                    value={formData.coordination.mode}
                    onValueChange={(value) => setFormData({
                      ...formData,
                      coordination: { ...formData.coordination, mode: value }
                    })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="sequential">Sequential</SelectItem>
                      <SelectItem value="parallel">Parallel</SelectItem>
                      <SelectItem value="collaborative">Collaborative</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label>MCP Tool Pool</Label>
                <div className="grid grid-cols-2 gap-2">
                  {mcpServers.length === 0 ? (
                    <p className="text-sm text-muted-foreground col-span-2">No MCP servers available</p>
                  ) : (
                    mcpServers.map(server => (
                      <div key={server.name} className="flex items-center space-x-2">
                        <Checkbox
                          id={`mcp-${server.name}`}
                          checked={formData.available_mcps.includes(server.name)}
                          onCheckedChange={() => toggleMcp(server.name)}
                        />
                        <label htmlFor={`mcp-${server.name}`} className="text-sm cursor-pointer">
                          {server.name}
                        </label>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>Team Agents</Label>
                  <Button type="button" size="sm" variant="outline" onClick={addAgent}>
                    <Plus className="h-3 w-3 mr-1" />
                    Add Agent
                  </Button>
                </div>

                {formData.agents.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-4">No agents added yet. Click "Add Agent" to add autonomous agents to the team.</p>
                ) : (
                  <div className="space-y-4">
                    {formData.agents.map((agent, index) => (
                      <Card key={index}>
                        <CardHeader className="pb-3">
                          <div className="flex items-center justify-between">
                            <CardTitle className="text-sm">Agent {index + 1}</CardTitle>
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              onClick={() => removeAgent(index)}
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                        </CardHeader>
                        <CardContent className="space-y-3">
                          <div className="space-y-2">
                            <Label>Agent ID</Label>
                            <Select
                              value={agent.agent_id}
                              onValueChange={(value) => updateAgent(index, 'agent_id', value)}
                            >
                              <SelectTrigger>
                                <SelectValue placeholder="Select an agent..." />
                              </SelectTrigger>
                              <SelectContent>
                                {availableAgents.map(a => (
                                  <SelectItem key={a.id} value={a.id}>
                                    {a.name} ({a.id})
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>

                          <div className="space-y-2">
                            <Label>Role in Team</Label>
                            <Input
                              required
                              value={agent.role}
                              onChange={(e) => updateAgent(index, 'role', e.target.value)}
                              placeholder="e.g., Lead Security Analyst"
                            />
                          </div>

                          <div className="space-y-2">
                            <Label className="text-xs">MCP Access Restrictions (Optional)</Label>
                            <p className="text-xs text-muted-foreground">Leave empty to grant access to all team MCPs</p>
                            <div className="grid grid-cols-2 gap-2">
                              {formData.available_mcps.length === 0 ? (
                                <p className="text-xs text-muted-foreground col-span-2">Select team MCPs first</p>
                              ) : (
                                formData.available_mcps.map(mcp => (
                                  <div key={mcp} className="flex items-center space-x-2">
                                    <Checkbox
                                      id={`agent-${index}-mcp-${mcp}`}
                                      checked={agent.mcp_access?.includes(mcp) || false}
                                      onCheckedChange={() => toggleAgentMcp(index, mcp)}
                                    />
                                    <label htmlFor={`agent-${index}-mcp-${mcp}`} className="text-xs cursor-pointer">
                                      {mcp}
                                    </label>
                                  </div>
                                ))
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={resetForm}>
                  Cancel
                </Button>
                <Button type="submit">
                  {editingTeam ? 'Update Team' : 'Create Team'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        {/* Run Team Modal */}
        <Dialog open={showRunModal} onOpenChange={setShowRunModal}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Play className="h-5 w-5" />
                Run {runningTeam?.name}
              </DialogTitle>
            </DialogHeader>

            {runningTeam && (
              <div className="space-y-4">
                <div className="p-3 bg-background rounded-md space-y-1 text-sm">
                  <div><strong>Agents:</strong> {runningTeam.agents?.length || 0}</div>
                  <div><strong>MCP Pool:</strong> {runningTeam.available_mcps?.join(', ')}</div>
                  <div><strong>Mode:</strong> {runningTeam.coordination?.mode || 'sequential'}</div>
                </div>

                <div className="space-y-2">
                  <Label>Task Description</Label>
                  <Textarea
                    value={teamTask}
                    onChange={(e) => setTeamTask(e.target.value)}
                    placeholder="Describe the task for the team to accomplish..."
                    rows={4}
                    disabled={executingTeam}
                  />
                </div>

                <Button
                  onClick={runTeam}
                  disabled={executingTeam || !teamTask.trim()}
                  className="w-full"
                >
                  {executingTeam ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Running Team...
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 mr-2" />
                      Run Team
                    </>
                  )}
                </Button>

                {/* Progress Log - Real-time updates via SSE */}
                {progressLog.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm flex items-center gap-2">
                        <Activity className="h-4 w-4" />
                        Progress Log
                        {executionId && (
                          <Badge variant="outline" className="text-xs font-mono">
                            {executionId.substring(0, 8)}...
                          </Badge>
                        )}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-1 max-h-60 overflow-y-auto text-xs font-mono bg-background p-3 rounded">
                        {progressLog.map((log, idx) => (
                          <div key={idx} className="text-muted-foreground">
                            {log}
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {teamResult && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Result</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {teamResult.status === 'error' ? (
                        <div className="text-sm text-destructive">
                          <strong>Error:</strong> {teamResult.error}
                        </div>
                      ) : (
                        <div className="space-y-3 text-sm">
                          <div>
                            <strong>Status:</strong> {teamResult.status}
                          </div>
                          <div>
                            <strong>Coordination:</strong> {teamResult.coordination_mode}
                          </div>
                          {teamResult.answer && (
                            <div>
                              <strong>Team Answer:</strong>
                              <pre className="mt-1 p-2 bg-background rounded text-xs whitespace-pre-wrap">
                                {teamResult.answer}
                              </pre>
                            </div>
                          )}
                          {teamResult.agent_results && teamResult.agent_results.length > 0 && (
                            <details className="mt-2">
                              <summary className="cursor-pointer font-medium">
                                Agent Results ({teamResult.agent_results.length})
                              </summary>
                              <div className="mt-2 space-y-2">
                                {teamResult.agent_results.map((result, idx) => (
                                  <div key={idx} className="p-2 bg-background rounded text-xs">
                                    <div className="font-medium">{result.role} ({result.agent_id})</div>
                                    <div>Status: {result.status}</div>
                                    <div>Iterations: {result.iterations}</div>
                                    {result.answer && (
                                      <div className="mt-1">Answer: {result.answer.substring(0, 200)}...</div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </details>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
