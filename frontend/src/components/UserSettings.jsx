/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Settings, Trash2, Moon, Sun, Monitor } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * User Settings Menu Component
 * Follows Unix philosophy: Simple, text-based configuration
 * Settings stored in workspace/user-config/user.conf per ADCL principles
 */
export default function UserSettings({ onClearHistory }) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [settings, setSettings] = useState({
    theme: 'system',
    log_level: 'info',
    mcp_timeout: '60',
    auto_save: true,
  });

  useEffect(() => {
    if (dialogOpen) {
      loadSettings();
    }
  }, [dialogOpen]);

  const loadSettings = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/settings`);
      setSettings(response.data);
    } catch (error) {
      console.error('Failed to load settings:', error);
      toast.warning('Using default settings (could not load from server)');
    }
  };

  const updateSetting = async (key, value) => {
    try {
      await axios.post(`${API_URL}/api/settings`, { key, value });
      setSettings({ ...settings, [key]: value });
      toast.success('Setting updated');
    } catch (error) {
      console.error('Failed to update setting:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to update setting';
      toast.error(errorMsg);
    }
  };

  const handleClearHistory = async () => {
    if (confirm('Clear all conversation history? This cannot be undone.')) {
      try {
        await onClearHistory();
        toast.success('History cleared');
      } catch (error) {
        console.error('Failed to clear history:', error);
        const errorMsg = error?.message || 'Failed to clear history';
        toast.error(errorMsg);
      }
    }
  };

  const themeOptions = [
    { value: 'light', label: 'Light', icon: Sun },
    { value: 'dark', label: 'Dark', icon: Moon },
    { value: 'system', label: 'System', icon: Monitor },
  ];

  const logLevelOptions = [
    { value: 'error', label: 'Error' },
    { value: 'info', label: 'Info' },
    { value: 'debug', label: 'Debug' },
  ];

  const timeoutOptions = [
    { value: '30', label: '30 seconds' },
    { value: '60', label: '60 seconds' },
    { value: '120', label: '120 seconds' },
  ];

  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        className="h-9 w-9 p-0"
        onClick={() => setDialogOpen(true)}
      >
        <Settings className="h-4 w-4" />
      </Button>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>User Settings</DialogTitle>
          </DialogHeader>

          <div className="space-y-6 py-4">
            {/* Theme Selection */}
            <div className="space-y-2">
              <Label>Theme</Label>
              <div className="grid grid-cols-3 gap-2">
                {themeOptions.map(({ value, label, icon: Icon }) => (
                  <Button
                    key={value}
                    variant={settings.theme === value ? 'default' : 'outline'}
                    size="sm"
                    className="w-full"
                    onClick={() => updateSetting('theme', value)}
                  >
                    <Icon className="h-4 w-4 mr-2" />
                    {label}
                  </Button>
                ))}
              </div>
            </div>

            {/* Log Level */}
            <div className="space-y-2">
              <Label>Log Level</Label>
              <div className="grid grid-cols-3 gap-2">
                {logLevelOptions.map(({ value, label }) => (
                  <Button
                    key={value}
                    variant={settings.log_level === value ? 'default' : 'outline'}
                    size="sm"
                    className="w-full"
                    onClick={() => updateSetting('log_level', value)}
                  >
                    {label}
                  </Button>
                ))}
              </div>
            </div>

            {/* MCP Timeout */}
            <div className="space-y-2">
              <Label>MCP Timeout</Label>
              <div className="grid grid-cols-3 gap-2">
                {timeoutOptions.map(({ value, label }) => (
                  <Button
                    key={value}
                    variant={settings.mcp_timeout === value ? 'default' : 'outline'}
                    size="sm"
                    className="w-full"
                    onClick={() => updateSetting('mcp_timeout', value)}
                  >
                    {label}
                  </Button>
                ))}
              </div>
            </div>

            {/* Auto-save Toggle */}
            <div className="flex items-center justify-between">
              <Label>Auto-save Drafts</Label>
              <Button
                variant={settings.auto_save ? 'default' : 'outline'}
                size="sm"
                onClick={() => updateSetting('auto_save', !settings.auto_save)}
              >
                <Badge
                  variant={settings.auto_save ? 'default' : 'outline'}
                  className="bg-transparent border-0"
                >
                  {settings.auto_save ? 'On' : 'Off'}
                </Badge>
              </Button>
            </div>

            {/* Clear History */}
            <div className="pt-4 border-t">
              <Button
                variant="destructive"
                size="sm"
                className="w-full"
                onClick={handleClearHistory}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Clear History
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
