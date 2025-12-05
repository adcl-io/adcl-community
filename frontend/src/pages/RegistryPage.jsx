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
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Package,
  Download,
  Play,
  Square,
  RefreshCw,
  Loader2,
  Users,
  Wrench,
  HardDrive,
  Trash2,
  ArrowUpCircle,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  X,
  Zap
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function RegistryPage() {
  const [catalog, setCatalog] = useState({ registries: [], mcps: [], teams: [], triggers: [] });
  const [installedMcps, setInstalledMcps] = useState([]);
  const [installedTriggers, setInstalledTriggers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [installing, setInstalling] = useState({});
  const [operating, setOperating] = useState({});
  const [message, setMessage] = useState(null);
  const [activeTab, setActiveTab] = useState('teams');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [showInstallModal, setShowInstallModal] = useState(false);
  const [selectedTrigger, setSelectedTrigger] = useState(null);
  const [targetConfig, setTargetConfig] = useState({ type: 'workflow', id: '' });
  const [teams, setTeams] = useState([]);
  const [teamsLoading, setTeamsLoading] = useState(false);
  const [teamsError, setTeamsError] = useState(null);

  useEffect(() => {
    loadCatalog();
    loadInstalledMcps();
    loadInstalledTriggers();
  }, []);

  // Auto-refresh installed MCPs and triggers status every 3 seconds
  useEffect(() => {
    if (!autoRefresh) return;
    if (activeTab !== 'installed' && activeTab !== 'installed-triggers') return;

    const interval = setInterval(() => {
      if (activeTab === 'installed') {
        loadInstalledMcps();
      } else if (activeTab === 'installed-triggers') {
        loadInstalledTriggers();
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [autoRefresh, activeTab]);

  const loadCatalog = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API_URL}/registries/catalog`);
      setCatalog(response.data);
    } catch (error) {
      console.error('Failed to load catalog:', error);
      setError('Failed to load registry catalog. Check registries.conf configuration.');
    } finally {
      setLoading(false);
    }
  };

  const loadInstalledMcps = async () => {
    try {
      const response = await axios.get(`${API_URL}/mcps/installed`);
      setInstalledMcps(response.data);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to load installed MCPs:', error);
    }
  };

  const loadInstalledTriggers = async () => {
    try {
      const response = await axios.get(`${API_URL}/triggers`);
      setInstalledTriggers(response.data);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to load installed triggers:', error);
    }
  };

  const loadTeams = async () => {
    setTeamsLoading(true);
    setTeamsError(null);
    try {
      const response = await axios.get(`${API_URL}/teams`);
      setTeams(response.data);
    } catch (error) {
      console.error('Failed to load teams:', error);
      setTeamsError('Failed to load teams');
    } finally {
      setTeamsLoading(false);
    }
  };

  const getStatusBadge = (mcp) => {
    const operation = operating[mcp.name];

    if (operation) {
      return {
        label: operation.charAt(0).toUpperCase() + operation.slice(1),
        variant: 'secondary',
        icon: <Loader2 className="h-3 w-3 animate-spin" />
      };
    }

    if (mcp.state === 'running') {
      return {
        label: 'Running',
        variant: 'default',
        icon: <CheckCircle2 className="h-3 w-3" />,
        className: 'bg-success/10 text-success hover:bg-success/20 border-success/30'
      };
    } else if (mcp.state === 'exited') {
      return {
        label: 'Stopped',
        variant: 'destructive',
        icon: <XCircle className="h-3 w-3" />,
        className: 'bg-destructive/10 text-destructive hover:bg-destructive/20 border-destructive/30'
      };
    } else if (mcp.state === 'container_missing') {
      return {
        label: 'Error',
        variant: 'destructive',
        icon: <AlertTriangle className="h-3 w-3" />,
        className: 'bg-warning/10 text-warning hover:bg-warning/20 border-warning/30'
      };
    } else {
      return {
        label: mcp.state || 'Unknown',
        variant: 'outline',
        icon: <AlertTriangle className="h-3 w-3" />
      };
    }
  };

  const formatUptime = (installedAt) => {
    if (!installedAt) return 'Unknown';
    const now = new Date();
    const installed = new Date(installedAt);
    const diff = now - installed;

    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const installTeam = async (teamId, registryId) => {
    const key = `${teamId}-${registryId}`;
    setInstalling(prev => ({ ...prev, [key]: true }));
    setMessage(null);

    try {
      const response = await axios.post(
        `${API_URL}/registries/install/team/${teamId}`,
        null,
        { params: { registry_id: registryId } }
      );

      setMessage({
        type: 'success',
        text: `Installed ${response.data.team} v${response.data.version} from ${response.data.registry}`
      });

      // Refresh catalog after installation
      setTimeout(() => {
        loadCatalog();
      }, 1000);
    } catch (error) {
      console.error('Failed to install team:', error);
      setMessage({
        type: 'error',
        text: `Failed to install team: ${error.response?.data?.detail || error.message}`
      });
    } finally {
      setInstalling(prev => ({ ...prev, [key]: false }));
    }
  };

  const installMcp = async (mcpId, registryId) => {
    const key = `${mcpId}-${registryId}`;
    setInstalling(prev => ({ ...prev, [key]: true }));
    setMessage(null);

    try {
      const response = await axios.post(
        `${API_URL}/registries/install/mcp/${mcpId}`,
        null,
        { params: { registry_id: registryId } }
      );

      setMessage({
        type: 'success',
        text: `Installed ${response.data.name} v${response.data.version} from ${response.data.registry}. Container: ${response.data.container_name}`
      });

      // Refresh both catalog and installed MCPs
      setTimeout(() => {
        loadCatalog();
        loadInstalledMcps();
      }, 1000);
    } catch (error) {
      console.error('Failed to install MCP:', error);
      setMessage({
        type: 'error',
        text: `Failed to install MCP: ${error.response?.data?.detail || error.message}`
      });
    } finally {
      setInstalling(prev => ({ ...prev, [key]: false }));
    }
  };

  const uninstallMcp = async (mcpName) => {
    if (!confirm(`Are you sure you want to uninstall ${mcpName}?`)) {
      return;
    }

    setOperating(prev => ({ ...prev, [mcpName]: 'uninstalling' }));
    setMessage(null);

    try {
      await axios.delete(`${API_URL}/mcps/${mcpName}`);

      setMessage({
        type: 'success',
        text: `Uninstalled ${mcpName}`
      });

      loadInstalledMcps();
    } catch (error) {
      console.error('Failed to uninstall MCP:', error);
      setMessage({
        type: 'error',
        text: `Failed to uninstall: ${error.response?.data?.detail || error.message}`
      });
    } finally {
      setOperating(prev => ({ ...prev, [mcpName]: null }));
    }
  };

  const startMcp = async (mcpName) => {
    setOperating(prev => ({ ...prev, [mcpName]: 'starting' }));
    try {
      await axios.post(`${API_URL}/mcps/${mcpName}/start`);
      setMessage({ type: 'success', text: `Started ${mcpName}` });
      loadInstalledMcps();
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to start: ${error.message}` });
    } finally {
      setOperating(prev => ({ ...prev, [mcpName]: null }));
    }
  };

  const stopMcp = async (mcpName) => {
    setOperating(prev => ({ ...prev, [mcpName]: 'stopping' }));
    try {
      await axios.post(`${API_URL}/mcps/${mcpName}/stop`);
      setMessage({ type: 'success', text: `Stopped ${mcpName}` });
      loadInstalledMcps();
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to stop: ${error.message}` });
    } finally {
      setOperating(prev => ({ ...prev, [mcpName]: null }));
    }
  };

  const restartMcp = async (mcpName) => {
    setOperating(prev => ({ ...prev, [mcpName]: 'restarting' }));
    try {
      await axios.post(`${API_URL}/mcps/${mcpName}/restart`);
      setMessage({ type: 'success', text: `Restarted ${mcpName}` });
      loadInstalledMcps();
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to restart: ${error.message}` });
    } finally {
      setOperating(prev => ({ ...prev, [mcpName]: null }));
    }
  };

  const updateMcp = async (mcpName) => {
    setOperating(prev => ({ ...prev, [mcpName]: 'updating' }));
    try {
      const response = await axios.post(`${API_URL}/mcps/${mcpName}/update`);
      if (response.data.status === 'updated') {
        setMessage({
          type: 'success',
          text: `Updated ${mcpName} from v${response.data.old_version} to v${response.data.new_version}`
        });
      } else {
        setMessage({ type: 'info', text: `${mcpName} is already at the latest version` });
      }
      loadInstalledMcps();
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to update: ${error.message}` });
    } finally {
      setOperating(prev => ({ ...prev, [mcpName]: null }));
    }
  };

  const openInstallTriggerModal = (trigger) => {
    setSelectedTrigger(trigger);
    setTargetConfig({ type: 'workflow', id: '' });
    setShowInstallModal(true);
    loadTeams(); // Load teams for the dropdown
  };

  const installTrigger = async () => {
    if (!selectedTrigger || !targetConfig.id) {
      setMessage({ type: 'error', text: 'Please specify a workflow or team ID' });
      return;
    }

    const key = `${selectedTrigger.id}-${selectedTrigger.registry}`;
    setInstalling(prev => ({ ...prev, [key]: true }));
    setMessage(null);

    try {
      const config = targetConfig.type === 'workflow'
        ? { workflow_id: targetConfig.id }
        : { team_id: targetConfig.id };

      const response = await axios.post(
        `${API_URL}/registries/install/trigger/${selectedTrigger.id}`,
        config,
        { params: { registry_id: selectedTrigger.registry } }
      );

      setMessage({
        type: 'success',
        text: `Installed ${response.data.trigger} v${response.data.version}`
      });

      setShowInstallModal(false);
      setSelectedTrigger(null);

      setTimeout(() => {
        loadCatalog();
        loadInstalledTriggers();
      }, 1000);
    } catch (error) {
      console.error('Failed to install trigger:', error);
      setMessage({
        type: 'error',
        text: `Failed to install trigger: ${error.response?.data?.detail || error.message}`
      });
    } finally {
      setInstalling(prev => ({ ...prev, [key]: false }));
    }
  };

  const uninstallTrigger = async (triggerName) => {
    if (!confirm(`Are you sure you want to uninstall ${triggerName}?`)) {
      return;
    }

    setOperating(prev => ({ ...prev, [triggerName]: 'uninstalling' }));
    setMessage(null);

    try {
      await axios.delete(`${API_URL}/triggers/${triggerName}`);
      setMessage({ type: 'success', text: `Uninstalled ${triggerName}` });
      loadInstalledTriggers();
    } catch (error) {
      console.error('Failed to uninstall trigger:', error);
      setMessage({
        type: 'error',
        text: `Failed to uninstall: ${error.response?.data?.detail || error.message}`
      });
    } finally {
      setOperating(prev => ({ ...prev, [triggerName]: null }));
    }
  };

  const startTrigger = async (triggerName) => {
    setOperating(prev => ({ ...prev, [triggerName]: 'starting' }));
    try {
      await axios.post(`${API_URL}/triggers/${triggerName}/start`);
      setMessage({ type: 'success', text: `Started ${triggerName}` });
      loadInstalledTriggers();
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to start: ${error.message}` });
    } finally {
      setOperating(prev => ({ ...prev, [triggerName]: null }));
    }
  };

  const stopTrigger = async (triggerName) => {
    setOperating(prev => ({ ...prev, [triggerName]: 'stopping' }));
    try {
      await axios.post(`${API_URL}/triggers/${triggerName}/stop`);
      setMessage({ type: 'success', text: `Stopped ${triggerName}` });
      loadInstalledTriggers();
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to stop: ${error.message}` });
    } finally {
      setOperating(prev => ({ ...prev, [triggerName]: null }));
    }
  };

  const restartTrigger = async (triggerName) => {
    setOperating(prev => ({ ...prev, [triggerName]: 'restarting' }));
    try {
      await axios.post(`${API_URL}/triggers/${triggerName}/restart`);
      setMessage({ type: 'success', text: `Restarted ${triggerName}` });
      loadInstalledTriggers();
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to restart: ${error.message}` });
    } finally {
      setOperating(prev => ({ ...prev, [triggerName]: null }));
    }
  };

  const updateTrigger = async (triggerName) => {
    setOperating(prev => ({ ...prev, [triggerName]: 'updating' }));
    try {
      const response = await axios.post(`${API_URL}/triggers/${triggerName}/update`);
      if (response.data.status === 'updated') {
        setMessage({
          type: 'success',
          text: `Updated ${triggerName} from v${response.data.old_version} to v${response.data.new_version}`
        });
      } else {
        setMessage({ type: 'info', text: `${triggerName} is already at the latest version` });
      }
      loadInstalledTriggers();
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to update: ${error.message}` });
    } finally {
      setOperating(prev => ({ ...prev, [triggerName]: null }));
    }
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
        <div className="flex justify-between items-start mb-8">
          <div>
            <h1 className="text-3xl font-bold text-foreground flex items-center gap-2">
              <Package className="h-8 w-8" />
              Package Registry
            </h1>
            <p className="text-muted-foreground mt-1">Browse and install MCPs and teams from configured registries</p>
          </div>
          <Button onClick={loadCatalog} variant="default">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh Catalog
          </Button>
        </div>

        {message && (
          <Alert className={`mb-6 ${message.type === 'success' ? 'border-success/30 bg-success/10' : message.type === 'error' ? 'border-destructive/30 bg-destructive/10' : 'border-info/30 bg-info/10'}`}>
            <div className="flex items-center justify-between">
              <AlertDescription className={message.type === 'success' ? 'text-success' : message.type === 'error' ? 'text-destructive' : 'text-info'}>
                {message.text}
              </AlertDescription>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setMessage(null)}
                className="h-6 w-6 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </Alert>
        )}

        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription className="flex items-center justify-between flex-1 ml-2">
              <span>{error}</span>
              <Button variant="outline" size="sm" onClick={loadCatalog}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {/* Registries Status */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HardDrive className="h-5 w-5" />
              Configured Registries
            </CardTitle>
          </CardHeader>
          <CardContent>
            {catalog.registries.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground border-2 border-dashed border-border rounded-lg">
                <p>No registries configured. Edit registries.conf to add registry sources.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {catalog.registries.map(registry => (
                  <Card
                    key={registry.id}
                    className={registry.available ? 'border-success/30 bg-success/5' : 'border-destructive/30 bg-destructive/5'}
                  >
                    <CardHeader className="pb-3">
                      <div className="flex items-start gap-3">
                        {registry.available ? (
                          <CheckCircle2 className="h-5 w-5 text-success mt-0.5" />
                        ) : (
                          <XCircle className="h-5 w-5 text-destructive mt-0.5" />
                        )}
                        <div className="flex-1 min-w-0">
                          <CardTitle className="text-sm">{registry.name}</CardTitle>
                          <code className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded break-all">
                            {registry.url}
                          </code>
                        </div>
                      </div>
                    </CardHeader>
                    {!registry.available && registry.error && (
                      <CardContent className="pt-0">
                        <p className="text-xs text-destructive border-t border-destructive/30 pt-2">
                          Error: {registry.error}
                        </p>
                      </CardContent>
                    )}
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Package Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="teams" className="flex items-center gap-2">
              <Users className="h-4 w-4" />
              Teams ({catalog.teams.length})
            </TabsTrigger>
            <TabsTrigger value="mcps" className="flex items-center gap-2">
              <Wrench className="h-4 w-4" />
              MCPs ({catalog.mcps.length})
            </TabsTrigger>
            <TabsTrigger value="triggers" className="flex items-center gap-2">
              <Zap className="h-4 w-4" />
              Triggers ({catalog.triggers.length})
              <Badge className="bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/20 text-xs ml-1">
                Experimental
              </Badge>
            </TabsTrigger>
            <TabsTrigger value="installed" className="flex items-center gap-2">
              <HardDrive className="h-4 w-4" />
              Installed MCPs ({installedMcps.length})
            </TabsTrigger>
            <TabsTrigger value="installed-triggers" className="flex items-center gap-2">
              <Zap className="h-4 w-4" />
              Installed Triggers ({installedTriggers.length})
              <Badge className="bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/20 text-xs ml-1">
                Experimental
              </Badge>
            </TabsTrigger>
          </TabsList>

          {/* Auto-refresh toggle for Installed tabs */}
          {((activeTab === 'installed' && installedMcps.length > 0) ||
            (activeTab === 'installed-triggers' && installedTriggers.length > 0)) && (
            <Card className="mt-4">
              <CardContent className="flex items-center justify-between py-3">
                <div className="flex items-center gap-3">
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="auto-refresh"
                      checked={autoRefresh}
                      onCheckedChange={setAutoRefresh}
                    />
                    <Label htmlFor="auto-refresh" className="text-sm font-medium cursor-pointer">
                      Auto-refresh (3s)
                    </Label>
                  </div>
                  {lastUpdate && (
                    <Badge variant="outline" className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      Last update: {lastUpdate.toLocaleTimeString()}
                    </Badge>
                  )}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={activeTab === 'installed' ? loadInstalledMcps : loadInstalledTriggers}
                >
                  <RefreshCw className="h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          )}

          <TabsContent value="teams" className="mt-6">
            {catalog.teams.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <Users className="h-12 w-12 mx-auto mb-2 text-muted-foreground" />
                <p>No teams available in configured registries.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {catalog.teams.map((team, index) => (
                  <Card key={`${team.id}-${index}`} className="hover:shadow-lg transition-shadow">
                    <CardHeader>
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-gradient-to-br from-purple-500 to-purple-700 rounded-lg">
                          <Users className="h-5 w-5 text-white" />
                        </div>
                        <div className="flex-1">
                          <CardTitle className="text-base">{team.name}</CardTitle>
                          <div className="flex gap-2 mt-2">
                            <Badge variant="secondary" className="text-xs">
                              v{team.version}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              {team.agents} agents
                            </Badge>
                          </div>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-muted-foreground mb-4">{team.description}</p>
                      <div className="flex items-center justify-between pt-3 border-t">
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Package className="h-3 w-3" />
                          {team.registry_name}
                        </div>
                        <Button
                          size="sm"
                          onClick={() => installTeam(team.id, team.registry)}
                          disabled={installing[`${team.id}-${team.registry}`]}
                        >
                          {installing[`${team.id}-${team.registry}`] ? (
                            <>
                              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                              Installing...
                            </>
                          ) : (
                            <>
                              <Download className="h-4 w-4 mr-2" />
                              Install
                            </>
                          )}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="mcps" className="mt-6">
            {catalog.mcps.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <Wrench className="h-12 w-12 mx-auto mb-2 text-muted-foreground" />
                <p>No MCPs available in configured registries.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {catalog.mcps.map((mcp, index) => (
                  <Card key={`${mcp.id}-${index}`} className="hover:shadow-lg transition-shadow">
                    <CardHeader>
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-gradient-to-br from-purple-500 to-purple-700 rounded-lg">
                          <Wrench className="h-5 w-5 text-white" />
                        </div>
                        <div className="flex-1">
                          <CardTitle className="text-base">{mcp.name}</CardTitle>
                          <Badge variant="secondary" className="text-xs mt-2">
                            v{mcp.version}
                          </Badge>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-muted-foreground mb-4">{mcp.description}</p>
                      <div className="flex items-center justify-between pt-3 border-t">
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Package className="h-3 w-3" />
                          {mcp.registry_name}
                        </div>
                        <Button
                          size="sm"
                          onClick={() => installMcp(mcp.id, mcp.registry)}
                          disabled={installing[`${mcp.id}-${mcp.registry}`]}
                        >
                          {installing[`${mcp.id}-${mcp.registry}`] ? (
                            <>
                              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                              Installing...
                            </>
                          ) : (
                            <>
                              <Download className="h-4 w-4 mr-2" />
                              Install
                            </>
                          )}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="installed" className="mt-6">
            {installedMcps.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <HardDrive className="h-12 w-12 mx-auto mb-2 text-muted-foreground" />
                <p>No MCPs installed yet. Install MCPs from the MCPs tab.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {installedMcps.map((mcp, index) => {
                  const statusBadge = getStatusBadge(mcp);
                  return (
                    <Card key={`installed-${mcp.name}-${index}`} className="hover:shadow-lg transition-shadow">
                      <CardHeader>
                        <div className="flex items-start gap-3">
                          <div className="p-2 bg-gradient-to-br from-purple-500 to-purple-700 rounded-lg">
                            <Wrench className="h-5 w-5 text-white" />
                          </div>
                          <div className="flex-1">
                            <CardTitle className="text-base">{mcp.name}</CardTitle>
                            <div className="flex gap-2 mt-2">
                              <Badge variant="secondary" className="text-xs">
                                v{mcp.version}
                              </Badge>
                              <Badge
                                variant={statusBadge.variant}
                                className={`text-xs flex items-center gap-1 ${statusBadge.className || ''}`}
                              >
                                {statusBadge.icon}
                                {statusBadge.label}
                              </Badge>
                            </div>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="bg-background rounded-lg p-3 space-y-2 text-xs">
                          <div className="flex justify-between items-center">
                            <span className="font-medium text-muted-foreground">Container:</span>
                            <code className="text-foreground bg-muted px-2 py-0.5 rounded">
                              {mcp.container_name}
                            </code>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="font-medium text-muted-foreground">State:</span>
                            <span className="text-foreground">{mcp.state}</span>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="font-medium text-muted-foreground">Uptime:</span>
                            <span className="text-foreground">{formatUptime(mcp.installed_at)}</span>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="font-medium text-muted-foreground">Installed:</span>
                            <span className="text-foreground">
                              {new Date(mcp.installed_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>

                        <div className="flex flex-wrap gap-2 pt-3 border-t">
                          {mcp.running ? (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => stopMcp(mcp.name)}
                                disabled={operating[mcp.name]}
                                className="flex-1"
                              >
                                {operating[mcp.name] === 'stopping' ? (
                                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                ) : (
                                  <Square className="h-3 w-3 mr-1" />
                                )}
                                Stop
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => restartMcp(mcp.name)}
                                disabled={operating[mcp.name]}
                                className="flex-1"
                              >
                                {operating[mcp.name] === 'restarting' ? (
                                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                ) : (
                                  <RefreshCw className="h-3 w-3 mr-1" />
                                )}
                                Restart
                              </Button>
                            </>
                          ) : (
                            <Button
                              variant="default"
                              size="sm"
                              onClick={() => startMcp(mcp.name)}
                              disabled={operating[mcp.name]}
                              className="flex-1"
                            >
                              {operating[mcp.name] === 'starting' ? (
                                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                              ) : (
                                <Play className="h-3 w-3 mr-1" />
                              )}
                              Start
                            </Button>
                          )}
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => updateMcp(mcp.name)}
                            disabled={operating[mcp.name]}
                            className="flex-1"
                          >
                            {operating[mcp.name] === 'updating' ? (
                              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                            ) : (
                              <ArrowUpCircle className="h-3 w-3 mr-1" />
                            )}
                            Update
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => uninstallMcp(mcp.name)}
                            disabled={operating[mcp.name]}
                            className="w-full"
                          >
                            {operating[mcp.name] === 'uninstalling' ? (
                              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                            ) : (
                              <Trash2 className="h-3 w-3 mr-1" />
                            )}
                            Uninstall
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </TabsContent>

          <TabsContent value="triggers" className="mt-6">
            {catalog.triggers.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <Zap className="h-12 w-12 mx-auto mb-2 text-muted-foreground" />
                <p>No triggers available in configured registries.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {catalog.triggers.map((trigger, index) => (
                  <Card key={`${trigger.id}-${index}`} className="hover:shadow-lg transition-shadow">
                    <CardHeader>
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-gradient-to-br from-amber-500 to-orange-700 rounded-lg">
                          <Zap className="h-5 w-5 text-white" />
                        </div>
                        <div className="flex-1">
                          <CardTitle className="text-base">{trigger.name}</CardTitle>
                          <div className="flex gap-2 mt-2">
                            <Badge variant="secondary" className="text-xs">
                              v{trigger.version}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              {trigger.trigger?.type || 'trigger'}
                            </Badge>
                          </div>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-muted-foreground mb-4">{trigger.description}</p>
                      <div className="flex items-center justify-between pt-3 border-t">
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Package className="h-3 w-3" />
                          {trigger.registry_name}
                        </div>
                        <Button
                          size="sm"
                          onClick={() => openInstallTriggerModal(trigger)}
                          disabled={installing[`${trigger.id}-${trigger.registry}`]}
                        >
                          {installing[`${trigger.id}-${trigger.registry}`] ? (
                            <>
                              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                              Installing...
                            </>
                          ) : (
                            <>
                              <Download className="h-4 w-4 mr-2" />
                              Install
                            </>
                          )}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="installed-triggers" className="mt-6">
            {installedTriggers.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <Zap className="h-12 w-12 mx-auto mb-2 text-muted-foreground" />
                <p>No triggers installed yet. Install triggers from the Triggers tab.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {installedTriggers.map((trigger, index) => {
                  const statusBadge = getStatusBadge(trigger);
                  return (
                    <Card key={`installed-trigger-${trigger.name}-${index}`} className="hover:shadow-lg transition-shadow">
                      <CardHeader>
                        <div className="flex items-start gap-3">
                          <div className="p-2 bg-gradient-to-br from-amber-500 to-orange-700 rounded-lg">
                            <Zap className="h-5 w-5 text-white" />
                          </div>
                          <div className="flex-1">
                            <CardTitle className="text-base">{trigger.name}</CardTitle>
                            <div className="flex gap-2 mt-2">
                              <Badge variant="secondary" className="text-xs">
                                v{trigger.version}
                              </Badge>
                              <Badge
                                variant={statusBadge.variant}
                                className={`text-xs flex items-center gap-1 ${statusBadge.className || ''}`}
                              >
                                {statusBadge.icon}
                                {statusBadge.label}
                              </Badge>
                            </div>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="bg-background rounded-lg p-3 space-y-2 text-xs">
                          <div className="flex justify-between items-center">
                            <span className="font-medium text-muted-foreground">Type:</span>
                            <span className="text-foreground">{trigger.trigger_type}</span>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="font-medium text-muted-foreground">Container:</span>
                            <code className="text-foreground bg-muted px-2 py-0.5 rounded">
                              {trigger.container_name}
                            </code>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="font-medium text-muted-foreground">State:</span>
                            <span className="text-foreground">{trigger.state}</span>
                          </div>
                          {trigger.workflow_id && (
                            <div className="flex justify-between items-center">
                              <span className="font-medium text-muted-foreground">Workflow:</span>
                              <code className="text-foreground bg-muted px-2 py-0.5 rounded">
                                {trigger.workflow_id}
                              </code>
                            </div>
                          )}
                          {trigger.team_id && (
                            <div className="flex justify-between items-center">
                              <span className="font-medium text-muted-foreground">Team:</span>
                              <code className="text-foreground bg-muted px-2 py-0.5 rounded">
                                {trigger.team_id}
                              </code>
                            </div>
                          )}
                          <div className="flex justify-between items-center">
                            <span className="font-medium text-muted-foreground">Installed:</span>
                            <span className="text-foreground">
                              {new Date(trigger.installed_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>

                        <div className="flex flex-wrap gap-2 pt-3 border-t">
                          {trigger.running ? (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => stopTrigger(trigger.name)}
                                disabled={operating[trigger.name]}
                                className="flex-1"
                              >
                                {operating[trigger.name] === 'stopping' ? (
                                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                ) : (
                                  <Square className="h-3 w-3 mr-1" />
                                )}
                                Stop
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => restartTrigger(trigger.name)}
                                disabled={operating[trigger.name]}
                                className="flex-1"
                              >
                                {operating[trigger.name] === 'restarting' ? (
                                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                ) : (
                                  <RefreshCw className="h-3 w-3 mr-1" />
                                )}
                                Restart
                              </Button>
                            </>
                          ) : (
                            <Button
                              variant="default"
                              size="sm"
                              onClick={() => startTrigger(trigger.name)}
                              disabled={operating[trigger.name]}
                              className="flex-1"
                            >
                              {operating[trigger.name] === 'starting' ? (
                                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                              ) : (
                                <Play className="h-3 w-3 mr-1" />
                              )}
                              Start
                            </Button>
                          )}
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => updateTrigger(trigger.name)}
                            disabled={operating[trigger.name]}
                            className="flex-1"
                          >
                            {operating[trigger.name] === 'updating' ? (
                              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                            ) : (
                              <ArrowUpCircle className="h-3 w-3 mr-1" />
                            )}
                            Update
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => uninstallTrigger(trigger.name)}
                            disabled={operating[trigger.name]}
                            className="w-full"
                          >
                            {operating[trigger.name] === 'uninstalling' ? (
                              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                            ) : (
                              <Trash2 className="h-3 w-3 mr-1" />
                            )}
                            Uninstall
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </TabsContent>
        </Tabs>

        {/* Install Trigger Modal */}
        {showInstallModal && selectedTrigger && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowInstallModal(false)}>
            <Card className="w-full max-w-md m-4" onClick={(e) => e.stopPropagation()}>
              <CardHeader>
                <CardTitle>Install Trigger: {selectedTrigger.name}</CardTitle>
                <CardDescription>
                  Specify which workflow or team this trigger should execute
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Target Type</Label>
                  <div className="flex gap-2">
                    <Button
                      variant={targetConfig.type === 'workflow' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setTargetConfig({ type: 'workflow', id: '' })}
                      className="flex-1"
                    >
                      Workflow
                    </Button>
                    <Button
                      variant={targetConfig.type === 'team' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setTargetConfig({ type: 'team', id: '' })}
                      className="flex-1"
                    >
                      Team
                    </Button>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="target-id">
                    {targetConfig.type === 'workflow' ? 'Workflow ID' : 'Team'}
                  </Label>
                  {targetConfig.type === 'team' ? (
                    <div className="space-y-2">
                      {teamsLoading ? (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Loading teams...
                        </div>
                      ) : teamsError ? (
                        <div className="text-sm text-destructive">{teamsError}</div>
                      ) : (
                        <Select
                          value={targetConfig.id}
                          onValueChange={(value) => setTargetConfig({ ...targetConfig, id: value })}
                        >
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select a team" />
                          </SelectTrigger>
                          <SelectContent>
                            {teams.map((team) => (
                              <SelectItem key={team.id} value={team.id}>
                                <div className="flex flex-col">
                                  <span className="font-medium">{team.name}</span>
                                  <span className="text-xs text-muted-foreground">ID: {team.id}</span>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    </div>
                  ) : (
                    <input
                      id="target-id"
                      type="text"
                      value={targetConfig.id}
                      onChange={(e) => setTargetConfig({ ...targetConfig, id: e.target.value })}
                      placeholder="Enter workflow ID"
                      className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  )}
                </div>
              </CardContent>
              <div className="flex gap-2 p-6 pt-0">
                <Button
                  variant="outline"
                  onClick={() => setShowInstallModal(false)}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  onClick={installTrigger}
                  disabled={!targetConfig.id || installing[`${selectedTrigger.id}-${selectedTrigger.registry}`]}
                  className="flex-1"
                >
                  {installing[`${selectedTrigger.id}-${selectedTrigger.registry}`] ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Installing...
                    </>
                  ) : (
                    'Install'
                  )}
                </Button>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
