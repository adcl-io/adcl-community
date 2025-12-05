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
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Cpu, Loader2, Play, ChevronDown, Edit2, Save, X, Plus, Trash2,
  AlertCircle, Check, Settings
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function AgentsPage() {
  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [runningAgent, setRunningAgent] = useState(false);
  const [agentTask, setAgentTask] = useState('');
  const [agentResult, setAgentResult] = useState(null);

  // Edit mode state
  const [editMode, setEditMode] = useState(false);
  const [editedAgent, setEditedAgent] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState(null);

  // MCP servers for dropdown
  const [availableMcps, setAvailableMcps] = useState([]);

  // Available models for dropdown
  const [availableModels, setAvailableModels] = useState([]);

  useEffect(() => {
    fetchAgents();
    fetchMcpServers();
    fetchModels();
  }, []);

  const fetchAgents = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/agents`);
      setAgents(response.data);
    } catch (error) {
      console.error('Error fetching agents:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchMcpServers = async () => {
    try {
      const response = await axios.get(`${API_URL}/mcp/servers`);
      setAvailableMcps(response.data.map(s => s.name));
    } catch (error) {
      console.error('Error fetching MCP servers:', error);
    }
  };

  const fetchModels = async () => {
    try {
      const response = await axios.get(`${API_URL}/models`);
      // Only include configured models
      const configuredModels = response.data.filter(m => m.configured);
      setAvailableModels(configuredModels);
    } catch (error) {
      console.error('Error fetching models:', error);
    }
  };

  const runAgent = async () => {
    if (!selectedAgent || !agentTask.trim()) return;

    try {
      setRunningAgent(true);
      setAgentResult(null);

      const response = await axios.post(`${API_URL}/agents/run`, {
        agent_id: selectedAgent.id,
        task: agentTask,
        context: {}
      });

      setAgentResult(response.data);
    } catch (error) {
      console.error('Error running agent:', error);
      setAgentResult({
        status: 'error',
        error: error.response?.data?.detail || error.message
      });
    } finally {
      setRunningAgent(false);
    }
  };

  const handleAgentSelect = (agent) => {
    setSelectedAgent(agent);
    setAgentResult(null);
    setEditMode(false);
    setEditedAgent(null);
    setSaveMessage(null);
  };

  const handleEditClick = () => {
    setEditMode(true);
    setEditedAgent(JSON.parse(JSON.stringify(selectedAgent))); // Deep clone
    setSaveMessage(null);
  };

  const handleCancelEdit = () => {
    setEditMode(false);
    setEditedAgent(null);
    setSaveMessage(null);
  };

  const handleSaveAgent = async () => {
    try {
      setSaving(true);
      setSaveMessage(null);

      const response = await axios.put(`${API_URL}/agents/${selectedAgent.id}`, editedAgent);

      // Update local state
      setAgents(agents.map(a => a.id === selectedAgent.id ? response.data : a));
      setSelectedAgent(response.data);
      setEditMode(false);
      setEditedAgent(null);

      setSaveMessage({ type: 'success', text: 'Agent saved successfully!' });
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (error) {
      console.error('Error saving agent:', error);
      setSaveMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to save agent'
      });
    } finally {
      setSaving(false);
    }
  };

  const handleCreateNewAgent = async () => {
    // Get default model or first configured model
    const defaultModel = availableModels.find(m => m.is_default) || availableModels[0];
    const modelId = defaultModel?.model_id || 'claude-sonnet-4-20250514';

    const newAgent = {
      name: 'New Agent',
      description: 'A new autonomous agent',
      persona: {
        role: 'General Purpose Agent',
        expertise: [],
        behavior: '',
        system_prompt: ''
      },
      available_mcps: [],
      capabilities: {
        autonomous: true,
        max_iterations: 10,
        can_loop: true,
        requires_approval: false
      },
      model_config: {
        model: modelId,
        temperature: 0.7,
        max_tokens: 4096
      },
      tags: [],
      author: '',
      version: '1.0.0'
    };

    try {
      setSaving(true);
      const response = await axios.post(`${API_URL}/agents`, newAgent);
      setAgents([...agents, response.data]);
      setSelectedAgent(response.data);
      setEditMode(true);
      setEditedAgent(JSON.parse(JSON.stringify(response.data)));
      setSaveMessage({ type: 'success', text: 'New agent created! Edit and save.' });
    } catch (error) {
      console.error('Error creating agent:', error);
      setSaveMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to create agent'
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAgent = async () => {
    if (!confirm(`Are you sure you want to delete "${selectedAgent.name}"?`)) return;

    try {
      setSaving(true);
      await axios.delete(`${API_URL}/agents/${selectedAgent.id}`);
      setAgents(agents.filter(a => a.id !== selectedAgent.id));
      setSelectedAgent(null);
      setEditMode(false);
      setEditedAgent(null);
      setSaveMessage({ type: 'success', text: 'Agent deleted successfully!' });
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (error) {
      console.error('Error deleting agent:', error);
      setSaveMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to delete agent'
      });
    } finally {
      setSaving(false);
    }
  };

  const updateEditedField = (path, value) => {
    const pathParts = path.split('.');
    const updated = { ...editedAgent };
    let current = updated;

    for (let i = 0; i < pathParts.length - 1; i++) {
      current = current[pathParts[i]];
    }

    current[pathParts[pathParts.length - 1]] = value;
    setEditedAgent(updated);
  };

  const addArrayItem = (path, value = '') => {
    const current = path.split('.').reduce((obj, key) => obj[key], editedAgent);
    updateEditedField(path, [...current, value]);
  };

  const removeArrayItem = (path, index) => {
    const current = path.split('.').reduce((obj, key) => obj[key], editedAgent);
    updateEditedField(path, current.filter((_, i) => i !== index));
  };

  const updateArrayItem = (path, index, value) => {
    const current = path.split('.').reduce((obj, key) => obj[key], editedAgent);
    const updated = [...current];
    updated[index] = value;
    updateEditedField(path, updated);
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
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground flex items-center gap-2">
              <Cpu className="h-8 w-8" />
              Autonomous Agents
            </h1>
            <p className="text-muted-foreground mt-1">AI agents that can autonomously use tools to complete complex tasks</p>
          </div>
          <Button onClick={handleCreateNewAgent} disabled={saving}>
            <Plus className="h-4 w-4 mr-2" />
            New Agent
          </Button>
        </div>

        {saveMessage && (
          <Alert
            className="mb-4"
            variant={saveMessage.type === 'error' ? 'destructive' : 'default'}
          >
            {saveMessage.type === 'success' ? (
              <Check className="h-4 w-4" />
            ) : (
              <AlertCircle className="h-4 w-4" />
            )}
            <AlertDescription>{saveMessage.text}</AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Agent List */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle>Available Agents</CardTitle>
                <CardDescription>{editMode ? 'Select to edit' : 'Select to run or edit'}</CardDescription>
              </CardHeader>
              <CardContent>
                {agents.length === 0 ? (
                  <div className="text-center py-8 text-sm text-muted-foreground">
                    <Cpu className="h-12 w-12 mx-auto mb-2 text-muted-foreground" />
                    <p>No agents configured</p>
                    <p className="text-xs mt-1">Click "New Agent" to create one</p>
                  </div>
                ) : (
                  <ScrollArea className="h-[600px]">
                    <div className="space-y-2">
                      {agents.map(agent => (
                        <Card
                          key={agent.id}
                          className={`cursor-pointer transition-all ${
                            selectedAgent?.id === agent.id
                              ? 'border-primary bg-primary/5'
                              : 'hover:border-primary/50'
                          }`}
                          onClick={() => handleAgentSelect(agent)}
                        >
                          <CardHeader className="p-4">
                            <CardTitle className="text-sm flex items-center gap-2">
                              <Cpu className="h-4 w-4" />
                              {agent.name}
                            </CardTitle>
                            {agent.persona?.role && (
                              <CardDescription className="text-xs">{agent.persona.role}</CardDescription>
                            )}
                          </CardHeader>
                          {(agent.tags || agent.available_mcps) && (
                            <CardContent className="p-4 pt-0 space-y-2">
                              {agent.tags && agent.tags.length > 0 && (
                                <div className="flex flex-wrap gap-1">
                                  {agent.tags.map(tag => (
                                    <Badge key={tag} variant="secondary" className="text-xs">
                                      {tag}
                                    </Badge>
                                  ))}
                                </div>
                              )}
                              {agent.available_mcps && agent.available_mcps.length > 0 && (
                                <div className="text-xs text-muted-foreground">
                                  <strong>Tools:</strong> {agent.available_mcps.join(', ')}
                                </div>
                              )}
                            </CardContent>
                          )}
                        </Card>
                      ))}
                    </div>
                  </ScrollArea>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Agent Detail/Editor */}
          <div className="lg:col-span-2">
            {!selectedAgent ? (
              <Card className="h-full flex items-center justify-center">
                <CardContent className="text-center py-12">
                  <Cpu className="h-16 w-16 mx-auto mb-4 text-muted-foreground" />
                  <h3 className="text-lg font-semibold text-foreground mb-2">No Agent Selected</h3>
                  <p className="text-muted-foreground">Select an agent to view, edit, or run tasks</p>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <Cpu className="h-5 w-5" />
                        {selectedAgent.name}
                      </CardTitle>
                      <CardDescription>
                        {selectedAgent.persona?.role || 'Autonomous agent'}
                      </CardDescription>
                    </div>
                    <div className="flex gap-2">
                      {editMode ? (
                        <>
                          <Button onClick={handleCancelEdit} variant="outline" disabled={saving}>
                            <X className="h-4 w-4 mr-2" />
                            Cancel
                          </Button>
                          <Button onClick={handleSaveAgent} disabled={saving}>
                            {saving ? (
                              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            ) : (
                              <Save className="h-4 w-4 mr-2" />
                            )}
                            Save
                          </Button>
                        </>
                      ) : (
                        <>
                          <Button onClick={handleEditClick} variant="outline">
                            <Edit2 className="h-4 w-4 mr-2" />
                            Edit
                          </Button>
                          <Button onClick={handleDeleteAgent} variant="destructive" disabled={saving}>
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <Tabs defaultValue={editMode ? "edit" : "run"} value={editMode ? "edit" : "run"}>
                    <TabsList className="grid w-full grid-cols-2">
                      <TabsTrigger value="run" disabled={editMode}>
                        <Play className="h-4 w-4 mr-2" />
                        Run Agent
                      </TabsTrigger>
                      <TabsTrigger value="edit" disabled={!editMode}>
                        <Settings className="h-4 w-4 mr-2" />
                        Configure
                      </TabsTrigger>
                    </TabsList>

                    {/* Run Tab */}
                    <TabsContent value="run" className="space-y-4 mt-4">
                      {selectedAgent.persona?.system_prompt && (
                        <div className="p-3 bg-muted rounded-md text-sm">
                          <strong>System Prompt:</strong>
                          <ScrollArea className="h-32 mt-2">
                            <pre className="text-xs whitespace-pre-wrap">{selectedAgent.persona.system_prompt}</pre>
                          </ScrollArea>
                        </div>
                      )}

                      <div className="space-y-2">
                        <Label htmlFor="task">Task Description</Label>
                        <Textarea
                          id="task"
                          value={agentTask}
                          onChange={(e) => setAgentTask(e.target.value)}
                          placeholder="Describe what you want the agent to do..."
                          rows={4}
                          disabled={runningAgent}
                        />
                      </div>

                      <Button
                        onClick={runAgent}
                        disabled={runningAgent || !agentTask.trim()}
                        className="w-full"
                      >
                        {runningAgent ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Running Agent...
                          </>
                        ) : (
                          <>
                            <Play className="h-4 w-4 mr-2" />
                            Run Agent
                          </>
                        )}
                      </Button>

                      {agentResult && (
                        <Card className="mt-4">
                          <CardHeader>
                            <CardTitle className="text-sm">Execution Result</CardTitle>
                          </CardHeader>
                          <CardContent>
                            {agentResult.status === 'error' ? (
                              <div className="text-sm text-destructive">
                                <strong>Error:</strong> {agentResult.error}
                              </div>
                            ) : (
                              <div className="space-y-4">
                                <div className="grid grid-cols-2 gap-4 text-sm">
                                  <div>
                                    <strong>Status:</strong> {agentResult.status}
                                  </div>
                                  <div>
                                    <strong>Iterations:</strong> {agentResult.iterations || 0}
                                  </div>
                                </div>

                                {agentResult.answer && (
                                  <div>
                                    <strong className="text-sm">Answer:</strong>
                                    <ScrollArea className="h-48 mt-2">
                                      <pre className="text-xs bg-muted p-3 rounded-md whitespace-pre-wrap">
                                        {agentResult.answer}
                                      </pre>
                                    </ScrollArea>
                                  </div>
                                )}

                                {agentResult.reasoning_steps && agentResult.reasoning_steps.length > 0 && (
                                  <details className="border rounded-md">
                                    <summary className="cursor-pointer p-3 hover:bg-muted flex items-center gap-2">
                                      <ChevronDown className="h-4 w-4" />
                                      <strong className="text-sm">Reasoning Steps ({agentResult.reasoning_steps.length})</strong>
                                    </summary>
                                    <div className="p-3 space-y-2 border-t">
                                      {agentResult.reasoning_steps.map((step, idx) => (
                                        <div key={idx} className="text-xs bg-muted p-2 rounded">
                                          <div className="font-medium">
                                            {typeof step === 'object' && step.iteration
                                              ? `Iteration ${step.iteration}`
                                              : `Step ${idx + 1}`}
                                          </div>
                                          <div className="text-muted-foreground mt-1 whitespace-pre-wrap">
                                            {typeof step === 'object'
                                              ? step.thinking || JSON.stringify(step, null, 2)
                                              : step}
                                          </div>
                                        </div>
                                      ))}
                                    </div>
                                  </details>
                                )}

                                {agentResult.tool_calls && agentResult.tool_calls.length > 0 && (
                                  <details className="border rounded-md">
                                    <summary className="cursor-pointer p-3 hover:bg-muted flex items-center gap-2">
                                      <ChevronDown className="h-4 w-4" />
                                      <strong className="text-sm">Tool Calls ({agentResult.tool_calls.length})</strong>
                                    </summary>
                                    <div className="p-3 space-y-2 border-t">
                                      {agentResult.tool_calls.map((call, idx) => (
                                        <div key={idx} className="text-xs bg-muted p-2 rounded">
                                          <div className="font-medium">{call.tool}</div>
                                          <pre className="text-muted-foreground mt-1 whitespace-pre-wrap">
                                            {JSON.stringify(call.params, null, 2)}
                                          </pre>
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
                    </TabsContent>

                    {/* Edit Tab */}
                    <TabsContent value="edit" className="space-y-4 mt-4">
                      {editedAgent && (
                        <ScrollArea className="h-[600px] pr-4">
                          <div className="space-y-6">
                            {/* Basic Info */}
                            <div className="space-y-4">
                              <h3 className="text-lg font-semibold">Basic Information</h3>

                              <div className="space-y-2">
                                <Label htmlFor="name">Agent Name</Label>
                                <Input
                                  id="name"
                                  value={editedAgent.name}
                                  onChange={(e) => updateEditedField('name', e.target.value)}
                                />
                              </div>

                              <div className="space-y-2">
                                <Label htmlFor="description">Description</Label>
                                <Textarea
                                  id="description"
                                  value={editedAgent.description}
                                  onChange={(e) => updateEditedField('description', e.target.value)}
                                  rows={2}
                                />
                              </div>

                              <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                  <Label htmlFor="version">Version</Label>
                                  <Input
                                    id="version"
                                    value={editedAgent.version}
                                    onChange={(e) => updateEditedField('version', e.target.value)}
                                  />
                                </div>
                                <div className="space-y-2">
                                  <Label htmlFor="author">Author</Label>
                                  <Input
                                    id="author"
                                    value={editedAgent.author}
                                    onChange={(e) => updateEditedField('author', e.target.value)}
                                  />
                                </div>
                              </div>

                              <div className="space-y-2">
                                <Label>Tags</Label>
                                <div className="flex flex-wrap gap-2">
                                  {editedAgent.tags?.map((tag, idx) => (
                                    <Badge key={idx} variant="secondary" className="flex items-center gap-1">
                                      {tag}
                                      <X
                                        className="h-3 w-3 cursor-pointer"
                                        onClick={() => removeArrayItem('tags', idx)}
                                      />
                                    </Badge>
                                  ))}
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => {
                                      const tag = prompt('Enter tag:');
                                      if (tag) addArrayItem('tags', tag);
                                    }}
                                  >
                                    <Plus className="h-3 w-3" />
                                  </Button>
                                </div>
                              </div>
                            </div>

                            {/* Persona */}
                            <div className="space-y-4 pt-4 border-t">
                              <h3 className="text-lg font-semibold">Persona</h3>

                              <div className="space-y-2">
                                <Label htmlFor="role">Role</Label>
                                <Input
                                  id="role"
                                  value={editedAgent.persona?.role || ''}
                                  onChange={(e) => updateEditedField('persona.role', e.target.value)}
                                />
                              </div>

                              <div className="space-y-2">
                                <Label htmlFor="behavior">Behavior</Label>
                                <Textarea
                                  id="behavior"
                                  value={editedAgent.persona?.behavior || ''}
                                  onChange={(e) => updateEditedField('persona.behavior', e.target.value)}
                                  rows={2}
                                />
                              </div>

                              <div className="space-y-2">
                                <Label htmlFor="system_prompt">System Prompt</Label>
                                <Textarea
                                  id="system_prompt"
                                  value={editedAgent.persona?.system_prompt || ''}
                                  onChange={(e) => updateEditedField('persona.system_prompt', e.target.value)}
                                  rows={8}
                                  className="font-mono text-sm"
                                />
                              </div>

                              <div className="space-y-2">
                                <Label>Expertise Areas</Label>
                                {editedAgent.persona?.expertise?.map((item, idx) => (
                                  <div key={idx} className="flex gap-2">
                                    <Input
                                      value={item}
                                      onChange={(e) => updateArrayItem('persona.expertise', idx, e.target.value)}
                                    />
                                    <Button
                                      variant="outline"
                                      size="icon"
                                      onClick={() => removeArrayItem('persona.expertise', idx)}
                                    >
                                      <X className="h-4 w-4" />
                                    </Button>
                                  </div>
                                ))}
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => addArrayItem('persona.expertise', '')}
                                >
                                  <Plus className="h-3 w-3 mr-2" />
                                  Add Expertise
                                </Button>
                              </div>
                            </div>

                            {/* Available MCPs */}
                            <div className="space-y-4 pt-4 border-t">
                              <h3 className="text-lg font-semibold">Available Tools (MCPs)</h3>
                              <div className="flex flex-wrap gap-2">
                                {availableMcps.map(mcp => (
                                  <Badge
                                    key={mcp}
                                    variant={editedAgent.available_mcps?.includes(mcp) ? "default" : "outline"}
                                    className="cursor-pointer"
                                    onClick={() => {
                                      const mcps = editedAgent.available_mcps || [];
                                      if (mcps.includes(mcp)) {
                                        updateEditedField('available_mcps', mcps.filter(m => m !== mcp));
                                      } else {
                                        updateEditedField('available_mcps', [...mcps, mcp]);
                                      }
                                    }}
                                  >
                                    {editedAgent.available_mcps?.includes(mcp) && <Check className="h-3 w-3 mr-1" />}
                                    {mcp}
                                  </Badge>
                                ))}
                              </div>
                            </div>

                            {/* Capabilities */}
                            <div className="space-y-4 pt-4 border-t">
                              <h3 className="text-lg font-semibold">Capabilities</h3>

                              <div className="space-y-2">
                                <Label htmlFor="max_iterations">Max Iterations</Label>
                                <Input
                                  id="max_iterations"
                                  type="number"
                                  value={editedAgent.capabilities?.max_iterations || 10}
                                  onChange={(e) => updateEditedField('capabilities.max_iterations', parseInt(e.target.value))}
                                />
                              </div>

                              <div className="flex items-center space-x-2">
                                <input
                                  type="checkbox"
                                  id="autonomous"
                                  checked={editedAgent.capabilities?.autonomous !== false}
                                  onChange={(e) => updateEditedField('capabilities.autonomous', e.target.checked)}
                                  className="rounded"
                                />
                                <Label htmlFor="autonomous">Autonomous (can run without user confirmation)</Label>
                              </div>

                              <div className="flex items-center space-x-2">
                                <input
                                  type="checkbox"
                                  id="can_loop"
                                  checked={editedAgent.capabilities?.can_loop !== false}
                                  onChange={(e) => updateEditedField('capabilities.can_loop', e.target.checked)}
                                  className="rounded"
                                />
                                <Label htmlFor="can_loop">Can Loop (iterate multiple times)</Label>
                              </div>

                              <div className="flex items-center space-x-2">
                                <input
                                  type="checkbox"
                                  id="requires_approval"
                                  checked={editedAgent.capabilities?.requires_approval === true}
                                  onChange={(e) => updateEditedField('capabilities.requires_approval', e.target.checked)}
                                  className="rounded"
                                />
                                <Label htmlFor="requires_approval">Requires Approval (ask before tool use)</Label>
                              </div>
                            </div>

                            {/* Model Config */}
                            <div className="space-y-4 pt-4 border-t">
                              <h3 className="text-lg font-semibold">Model Configuration</h3>

                              <div className="space-y-2">
                                <Label htmlFor="model">Model</Label>
                                <Select
                                  value={editedAgent.model_config?.model || ''}
                                  onValueChange={(value) => updateEditedField('model_config.model', value)}
                                >
                                  <SelectTrigger id="model">
                                    <SelectValue placeholder="Select a model" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {availableModels.length === 0 ? (
                                      <SelectItem value="" disabled>
                                        No models configured
                                      </SelectItem>
                                    ) : (
                                      availableModels.map((model) => (
                                        <SelectItem key={model.id} value={model.model_id}>
                                          {model.name} ({model.provider})
                                          {model.is_default && ' - Default'}
                                        </SelectItem>
                                      ))
                                    )}
                                  </SelectContent>
                                </Select>
                              </div>

                              <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                  <Label htmlFor="temperature">Temperature</Label>
                                  <Input
                                    id="temperature"
                                    type="number"
                                    step="0.1"
                                    min="0"
                                    max="1"
                                    value={editedAgent.model_config?.temperature || 0.7}
                                    onChange={(e) => updateEditedField('model_config.temperature', parseFloat(e.target.value))}
                                  />
                                </div>
                                <div className="space-y-2">
                                  <Label htmlFor="max_tokens">Max Tokens</Label>
                                  <Input
                                    id="max_tokens"
                                    type="number"
                                    value={editedAgent.model_config?.max_tokens || 4096}
                                    onChange={(e) => updateEditedField('model_config.max_tokens', parseInt(e.target.value))}
                                  />
                                </div>
                              </div>
                            </div>
                          </div>
                        </ScrollArea>
                      )}
                    </TabsContent>
                  </Tabs>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default AgentsPage;
