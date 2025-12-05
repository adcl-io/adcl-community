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
import {
  Bot,
  Plus,
  Edit,
  Trash2,
  Loader2,
  Brain,
  Lightbulb,
  CheckCircle2,
  AlertCircle,
  Star
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function ModelsPage() {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingModel, setEditingModel] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    provider: 'anthropic',
    model_id: 'claude-sonnet-4-5-20250929',
    api_key: '',
    temperature: 0.7,
    max_tokens: 4096,
    description: ''
  });

  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/models`);
      setModels(response.data);
    } catch (error) {
      console.error('Failed to load models:', error);
      // Load default models
      setModels([
        {
          id: 'claude-4-5',
          name: 'Claude Sonnet 4.5',
          provider: 'anthropic',
          model_id: 'claude-sonnet-4-5-20250929',
          temperature: 0.7,
          max_tokens: 4096,
          description: 'Advanced reasoning and coding capabilities',
          configured: true
        },
        {
          id: 'gpt-4',
          name: 'GPT-4',
          provider: 'openai',
          model_id: 'gpt-4',
          temperature: 0.7,
          max_tokens: 4096,
          description: 'OpenAI GPT-4 model',
          configured: false
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingModel) {
        await axios.put(`${API_URL}/models/${editingModel.id}`, formData);
      } else {
        await axios.post(`${API_URL}/models`, formData);
      }
      loadModels();
      resetForm();
    } catch (error) {
      console.error('Failed to save model:', error);
      alert('Failed to save model configuration');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this model configuration?')) return;

    try {
      await axios.delete(`${API_URL}/models/${id}`);
      loadModels();
    } catch (error) {
      console.error('Failed to delete model:', error);
      alert('Failed to delete model');
    }
  };

  const handleSetDefault = async (id) => {
    try {
      await axios.post(`${API_URL}/models/${id}/set-default`);
      loadModels();
    } catch (error) {
      console.error('Failed to set default model:', error);
      alert('Failed to set default model');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      provider: 'anthropic',
      model_id: 'claude-sonnet-4-5-20250929',
      api_key: '',
      temperature: 0.7,
      max_tokens: 4096,
      description: ''
    });
    setEditingModel(null);
    setShowAddModal(false);
  };

  const startEdit = (model) => {
    setEditingModel(model);
    setFormData({
      name: model.name,
      provider: model.provider,
      model_id: model.model_id,
      api_key: '',
      temperature: model.temperature,
      max_tokens: model.max_tokens,
      description: model.description || ''
    });
    setShowAddModal(true);
  };

  const providerModels = {
    anthropic: [
      { id: 'claude-sonnet-4-5-20250929', name: 'Claude Sonnet 4.5' },
      { id: 'claude-sonnet-4-20250514', name: 'Claude Sonnet 4' },
      { id: 'claude-opus-4-20250514', name: 'Claude Opus 4' }
    ],
    openai: [
      { id: 'gpt-4', name: 'GPT-4' },
      { id: 'gpt-4-turbo', name: 'GPT-4 Turbo' },
      { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo' }
    ]
  };

  const getProviderIcon = (provider) => {
    if (provider === 'anthropic') return Bot;
    if (provider === 'openai') return Brain;
    return Lightbulb;
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
              <Bot className="h-8 w-8" />
              Models
            </h1>
            <p className="text-muted-foreground mt-1">Configure LLM models for your agents</p>
          </div>
          <Button onClick={() => setShowAddModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Model
          </Button>
        </div>

        {models.length === 0 ? (
          <Card className="p-12">
            <div className="text-center">
              <Bot className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-xl font-semibold text-foreground mb-2">No Models Configured</h3>
              <p className="text-muted-foreground mb-6">Add your first LLM model to start building agents.</p>
              <Button onClick={() => setShowAddModal(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Your First Model
              </Button>
            </div>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {models.map(model => {
              const ProviderIcon = getProviderIcon(model.provider);
              return (
                <Card
                  key={model.id}
                  className={`hover:shadow-lg transition-shadow ${
                    model.configured
                      ? 'border-success/30 hover:border-success/50'
                      : 'border-warning/30 hover:border-warning/50'
                  }`}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-purple-700 flex items-center justify-center flex-shrink-0">
                          <ProviderIcon className="h-6 w-6 text-white" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <CardTitle className="text-lg truncate">{model.name}</CardTitle>
                          <Badge variant="secondary" className="mt-1 text-xs uppercase">
                            {model.provider}
                          </Badge>
                        </div>
                      </div>
                      <div className="flex-shrink-0 ml-2 flex flex-col gap-1">
                        {model.is_default && (
                          <Badge className="bg-amber-500/10 text-amber-600 dark:text-amber-400 hover:bg-amber-500/20 border-amber-500/30">
                            <Star className="h-3 w-3 mr-1 fill-current" />
                            DEFAULT
                          </Badge>
                        )}
                        {model.configured ? (
                          <Badge className="bg-success/10 text-success hover:bg-success/20 border-success/30">
                            <CheckCircle2 className="h-3 w-3 mr-1" />
                            Configured
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="bg-warning/10 text-warning hover:bg-warning/20 border-warning/30">
                            <AlertCircle className="h-3 w-3 mr-1" />
                            Not Configured
                          </Badge>
                        )}
                      </div>
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-4">
                    {model.description && (
                      <p className="text-sm text-muted-foreground">{model.description}</p>
                    )}

                    <div className="space-y-2 p-3 bg-muted rounded-lg">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-semibold text-foreground">Model ID:</span>
                        <code className="text-xs bg-muted-foreground/20 px-2 py-1 rounded">{model.model_id}</code>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-semibold text-foreground">Temperature:</span>
                        <span className="text-muted-foreground">{model.temperature}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-semibold text-foreground">Max Tokens:</span>
                        <span className="text-muted-foreground">{model.max_tokens.toLocaleString()}</span>
                      </div>
                    </div>

                    <div className="flex flex-col gap-2 pt-2 border-t">
                      {!model.is_default && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleSetDefault(model.id)}
                          className="w-full border-amber-500/30 text-amber-600 dark:text-amber-400 hover:bg-amber-500/10"
                        >
                          <Star className="h-3 w-3 mr-1" />
                          Set as Default
                        </Button>
                      )}
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" onClick={() => startEdit(model)} className="flex-1">
                          <Edit className="h-3 w-3 mr-1" />
                          Edit
                        </Button>
                        <Button size="sm" variant="destructive" onClick={() => handleDelete(model.id)}>
                          <Trash2 className="h-3 w-3 mr-1" />
                          Delete
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* Create/Edit Model Modal */}
        <Dialog open={showAddModal} onOpenChange={(open) => !open && resetForm()}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{editingModel ? 'Edit Model' : 'Add New Model'}</DialogTitle>
              <DialogDescription>
                Configure an LLM model for your agents to use
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="name">Model Name</Label>
                <Input
                  id="name"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Claude Sonnet 4.5"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="provider">Provider</Label>
                <Select
                  value={formData.provider}
                  onValueChange={(value) => setFormData({
                    ...formData,
                    provider: value,
                    model_id: providerModels[value][0].id
                  })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="anthropic">Anthropic</SelectItem>
                    <SelectItem value="openai">OpenAI</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="model_id">Model ID</Label>
                <Select
                  value={formData.model_id}
                  onValueChange={(value) => setFormData({ ...formData, model_id: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {providerModels[formData.provider].map(m => (
                      <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="api_key">API Key</Label>
                <Input
                  id="api_key"
                  type="password"
                  value={formData.api_key}
                  onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                  placeholder={editingModel ? "Leave blank to keep existing" : "sk-..."}
                />
                <p className="text-xs text-muted-foreground">Your API key is encrypted and stored securely</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="temperature">Temperature</Label>
                  <Input
                    id="temperature"
                    type="number"
                    min="0"
                    max="1"
                    step="0.1"
                    value={formData.temperature}
                    onChange={(e) => setFormData({ ...formData, temperature: parseFloat(e.target.value) })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="max_tokens">Max Tokens</Label>
                  <Input
                    id="max_tokens"
                    type="number"
                    min="1"
                    max="100000"
                    value={formData.max_tokens}
                    onChange={(e) => setFormData({ ...formData, max_tokens: parseInt(e.target.value) })}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Optional description"
                  rows={3}
                />
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button type="button" variant="outline" onClick={resetForm}>
                  Cancel
                </Button>
                <Button type="submit">
                  {editingModel ? 'Update Model' : 'Add Model'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
