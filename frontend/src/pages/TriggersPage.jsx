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
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Zap,
  RefreshCw,
  Loader2,
  Globe,
  Clock,
  Bell,
  Hand,
  Workflow,
  Users,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Play,
  Square,
  RotateCw,
  Trash2,
  Copy,
  Check
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function TriggersPage() {
  const [triggers, setTriggers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [operationLoading, setOperationLoading] = useState({});
  const [copiedUrl, setCopiedUrl] = useState(null);

  useEffect(() => {
    loadTriggers();
  }, []);

  const loadTriggers = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get(`${API_URL}/triggers`);
      setTriggers(response.data);
    } catch (err) {
      console.error('Error loading triggers:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load triggers');
    } finally {
      setLoading(false);
    }
  };

  const startTrigger = async (name) => {
    try {
      setOperationLoading(prev => ({ ...prev, [name]: 'starting' }));
      await axios.post(`${API_URL}/triggers/${name}/start`);
      await loadTriggers();
    } catch (err) {
      console.error(`Error starting trigger ${name}:`, err);
      alert(`Failed to start trigger: ${err.response?.data?.detail || err.message}`);
    } finally {
      setOperationLoading(prev => ({ ...prev, [name]: null }));
    }
  };

  const stopTrigger = async (name) => {
    try {
      setOperationLoading(prev => ({ ...prev, [name]: 'stopping' }));
      await axios.post(`${API_URL}/triggers/${name}/stop`);
      await loadTriggers();
    } catch (err) {
      console.error(`Error stopping trigger ${name}:`, err);
      alert(`Failed to stop trigger: ${err.response?.data?.detail || err.message}`);
    } finally {
      setOperationLoading(prev => ({ ...prev, [name]: null }));
    }
  };

  const restartTrigger = async (name) => {
    try {
      setOperationLoading(prev => ({ ...prev, [name]: 'restarting' }));
      await axios.post(`${API_URL}/triggers/${name}/restart`);
      await loadTriggers();
    } catch (err) {
      console.error(`Error restarting trigger ${name}:`, err);
      alert(`Failed to restart trigger: ${err.response?.data?.detail || err.message}`);
    } finally {
      setOperationLoading(prev => ({ ...prev, [name]: null }));
    }
  };

  const deleteTrigger = async (name) => {
    if (!confirm(`Are you sure you want to delete trigger "${name}"? This action cannot be undone.`)) {
      return;
    }

    try {
      setOperationLoading(prev => ({ ...prev, [name]: 'deleting' }));
      await axios.delete(`${API_URL}/triggers/${name}`);
      await loadTriggers();
    } catch (err) {
      console.error(`Error deleting trigger ${name}:`, err);
      alert(`Failed to delete trigger: ${err.response?.data?.detail || err.message}`);
    } finally {
      setOperationLoading(prev => ({ ...prev, [name]: null }));
    }
  };

  const copyToClipboard = async (text, id) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedUrl(id);
      setTimeout(() => setCopiedUrl(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const getTriggerIcon = (type) => {
    switch (type?.toLowerCase()) {
      case 'webhook': return Globe;
      case 'schedule': return Clock;
      case 'event': return Bell;
      case 'manual': return Hand;
      default: return Zap;
    }
  };

  const getStatusBadge = (trigger) => {
    if (trigger.state === 'running' || trigger.running) {
      return (
        <Badge className="bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20">
          <CheckCircle2 className="mr-1 h-3 w-3" />
          Running
        </Badge>
      );
    } else if (trigger.state === 'container_missing') {
      return (
        <Badge className="bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20">
          <AlertCircle className="mr-1 h-3 w-3" />
          Error
        </Badge>
      );
    } else {
      return (
        <Badge className="bg-gray-500/10 text-gray-700 dark:text-gray-400 border-gray-500/20">
          <XCircle className="mr-1 h-3 w-3" />
          Stopped
        </Badge>
      );
    }
  };

  const getTriggerTypeBadge = (type) => {
    const typeColors = {
      webhook: 'bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20',
      schedule: 'bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/20',
      event: 'bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/20',
      manual: 'bg-gray-500/10 text-gray-700 dark:text-gray-400 border-gray-500/20',
    };

    const colorClass = typeColors[type?.toLowerCase()] || typeColors.manual;

    return (
      <Badge className={colorClass}>
        {type || 'Unknown'}
      </Badge>
    );
  };

  const getEndpointUrl = (trigger) => {
    // Extract port from container_name or deployment config
    const ports = trigger.package?.deployment?.ports || [];
    if (ports.length > 0) {
      const port = ports[0].host;
      return `http://localhost:${port}`;
    }
    return null;
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
            <p className="mt-4 text-sm text-muted-foreground">Loading triggers...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center min-h-[400px]">
          <Card className="max-w-md">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-red-600">
                <AlertCircle className="h-5 w-5" />
                Error Loading Triggers
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">{error}</p>
              <Button onClick={loadTriggers} className="w-full">
                <RefreshCw className="mr-2 h-4 w-4" />
                Try Again
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Zap className="h-8 w-8" />
            Triggers
            <Badge className="bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/20">
              Experimental
            </Badge>
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage installed workflow and team triggers
          </p>
        </div>
        <Button onClick={loadTriggers} variant="outline" size="sm">
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Experimental Notice */}
      <Alert className="mb-6 bg-orange-500/5 border-orange-500/20">
        <AlertCircle className="h-4 w-4 text-orange-700 dark:text-orange-400" />
        <AlertDescription className="text-orange-700 dark:text-orange-400">
          Triggers are an experimental feature. APIs and functionality may change as we continue development.
        </AlertDescription>
      </Alert>

      {/* Empty State */}
      {triggers.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center">
            <Zap className="mx-auto h-12 w-12 text-muted-foreground/50" />
            <h3 className="mt-4 text-lg font-semibold">No triggers installed</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Install triggers from the Registry to get started
            </p>
          </CardContent>
        </Card>
      ) : (
        /* Triggers Grid */
        <div className="grid gap-6 md:grid-cols-2">
          {triggers.map((trigger) => {
            const TriggerIcon = getTriggerIcon(trigger.trigger_type);
            const isLoading = operationLoading[trigger.name];
            const endpointUrl = getEndpointUrl(trigger);

            return (
              <Card key={trigger.name} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-start gap-4">
                    <div className="rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 p-3 text-white">
                      <TriggerIcon className="h-6 w-6" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <CardTitle className="text-lg truncate">{trigger.name}</CardTitle>
                        {getStatusBadge(trigger)}
                      </div>
                      <div className="flex items-center gap-2 flex-wrap">
                        {getTriggerTypeBadge(trigger.trigger_type)}
                        <Badge variant="outline">{trigger.version}</Badge>
                      </div>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="space-y-3">
                  {/* Description */}
                  {trigger.package?.description && (
                    <p className="text-sm text-muted-foreground">
                      {trigger.package.description}
                    </p>
                  )}

                  {/* Target (Workflow or Team) */}
                  {trigger.user_config && (
                    <div className="flex items-center gap-2 text-sm">
                      {trigger.user_config.workflow_id ? (
                        <>
                          <Workflow className="h-4 w-4 text-muted-foreground" />
                          <span className="text-muted-foreground">Workflow:</span>
                          <code className="px-2 py-0.5 rounded bg-muted text-xs">
                            {trigger.user_config.workflow_id}
                          </code>
                        </>
                      ) : trigger.user_config.team_id ? (
                        <>
                          <Users className="h-4 w-4 text-muted-foreground" />
                          <span className="text-muted-foreground">Team:</span>
                          <code className="px-2 py-0.5 rounded bg-muted text-xs">
                            {trigger.user_config.team_id}
                          </code>
                        </>
                      ) : null}
                    </div>
                  )}

                  {/* Webhook Endpoints */}
                  {trigger.trigger_type === 'webhook' && endpointUrl && (
                    <div className="space-y-2">
                      <p className="text-xs font-medium text-muted-foreground">Endpoints:</p>
                      {(trigger.package?.trigger?.endpoints || []).map((endpoint, idx) => {
                        const fullUrl = `${endpointUrl}${endpoint.path}`;
                        const urlId = `${trigger.name}-${idx}`;
                        return (
                          <div key={idx} className="flex items-center gap-2">
                            <code className="flex-1 px-2 py-1 rounded bg-muted text-xs font-mono truncate">
                              {endpoint.method} {fullUrl}
                            </code>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => copyToClipboard(fullUrl, urlId)}
                              className="h-7 px-2"
                            >
                              {copiedUrl === urlId ? (
                                <Check className="h-3 w-3 text-green-600" />
                              ) : (
                                <Copy className="h-3 w-3" />
                              )}
                            </Button>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Installed timestamp */}
                  {trigger.installed_at && (
                    <p className="text-xs text-muted-foreground">
                      Installed: {new Date(trigger.installed_at).toLocaleString()}
                    </p>
                  )}

                  {/* Action Buttons */}
                  <div className="flex gap-2 pt-2">
                    {!trigger.running && trigger.state !== 'container_missing' && (
                      <Button
                        size="sm"
                        onClick={() => startTrigger(trigger.name)}
                        disabled={!!isLoading}
                      >
                        {isLoading === 'starting' ? (
                          <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                        ) : (
                          <Play className="mr-2 h-3 w-3" />
                        )}
                        Start
                      </Button>
                    )}

                    {trigger.running && (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => stopTrigger(trigger.name)}
                        disabled={!!isLoading}
                      >
                        {isLoading === 'stopping' ? (
                          <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                        ) : (
                          <Square className="mr-2 h-3 w-3" />
                        )}
                        Stop
                      </Button>
                    )}

                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => restartTrigger(trigger.name)}
                      disabled={!!isLoading}
                    >
                      {isLoading === 'restarting' ? (
                        <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                      ) : (
                        <RotateCw className="mr-2 h-3 w-3" />
                      )}
                      Restart
                    </Button>

                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => deleteTrigger(trigger.name)}
                      disabled={!!isLoading}
                      className="ml-auto"
                    >
                      {isLoading === 'deleting' ? (
                        <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                      ) : (
                        <Trash2 className="mr-2 h-3 w-3" />
                      )}
                      Delete
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
