/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React, { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ThemeToggleButton } from '@/components/ui/theme-toggle';
import {
  MessageSquare,
  Bot,
  Wrench,
  Users,
  Cpu,
  Package,
  Workflow,
  Rocket,
  Circle,
  Zap,
  History,
  Download
} from 'lucide-react';
import { useConversationHistoryContext } from '../contexts/ConversationHistoryContext';
import { UpgradeDialog } from './UpgradeDialog';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default function Navigation({ currentPage, onNavigate }) {
  const { sessions, loadSessions, loadSession } = useConversationHistoryContext();
  const recentSessions = sessions.slice(0, 10);
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [currentVersion, setCurrentVersion] = useState('0.1.0');
  const [upgradeDialogOpen, setUpgradeDialogOpen] = useState(false);

  useEffect(() => {
    loadSessions();
    checkForUpdates();
    // Check for updates every 1 hour
    const interval = setInterval(checkForUpdates, 60 * 60 * 1000);
    return () => clearInterval(interval);
  }, [loadSessions]);

  const checkForUpdates = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/system/updates/check`);
      if (response.ok) {
        const data = await response.json();
        setCurrentVersion(data.current_version);
        setUpdateAvailable(data.update_available);
      }
    } catch (error) {
      console.error('Failed to check for updates:', error);
    }
  };

  const handleLoadConversation = async (sessionId) => {
    await loadSession(sessionId);
    onNavigate('playground');
  };

  const pages = [
    { id: 'playground', label: 'Playground', icon: MessageSquare, hasSubmenu: true },
    { id: 'models', label: 'Models', icon: Bot },
    { id: 'mcps', label: 'MCP Servers', icon: Wrench },
    { id: 'teams', label: 'Teams', icon: Users },
    { id: 'agents', label: 'Agents', icon: Cpu },
    { id: 'registry', label: 'Registry', icon: Package },
    { id: 'workflows', label: 'Workflows', icon: Workflow },
    { id: 'triggers', label: 'Triggers', icon: Zap, experimental: true },
  ];

  return (
    <nav className="w-[250px] h-screen bg-card border-r border-border flex flex-col">
      <div className="p-6 border-b border-border">
        <h1 className="text-xl font-semibold flex items-center gap-2 text-foreground">
          <Rocket className="h-5 w-5" />
          MCP Agent Platform
        </h1>
        <p className="text-sm text-muted-foreground mt-1">Build and deploy agent teams</p>
      </div>

      <div className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
        {pages.map((page) => {
          const Icon = page.icon;
          
          if (page.hasSubmenu && page.id === 'playground') {
            return (
              <div key={page.id}>
                <Button
                  variant="ghost"
                  className={`w-full justify-start gap-3 h-11 px-4 text-sm font-normal ${
                    currentPage === page.id
                      ? 'bg-accent text-accent-foreground'
                      : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
                  }`}
                  onClick={() => onNavigate(page.id)}
                >
                  <Icon className="h-4 w-4" />
                  <span>{page.label}</span>
                </Button>
                
                {currentPage === 'playground' && (
                  <div className="mt-1 ml-4 space-y-1">
                    {recentSessions.length > 0 ? (
                      <>
                        {recentSessions
                          .filter(session => session.message_count > 0)
                          .slice(0, 8)
                          .map(session => {
                            // Generate display title - CSS handles truncation
                            const displayTitle = session.preview
                              ? session.preview.split('\n')[0]
                              : session.title !== 'New Conversation'
                                ? session.title
                                : `Chat ${new Date(session.updated).toLocaleDateString()} ${new Date(session.updated).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;

                            // Calculate relative time
                            const getRelativeTime = (timestamp) => {
                              // Handle both Unix timestamps and date strings
                              const date = typeof timestamp === 'number' ? new Date(timestamp * 1000) : new Date(timestamp);
                              const now = new Date();
                              const diffMs = now - date;
                              const diffMins = Math.floor(diffMs / 60000);
                              const diffHours = Math.floor(diffMs / 3600000);
                              const diffDays = Math.floor(diffMs / 86400000);

                              if (diffMins < 1) return 'now';
                              if (diffMins < 60) return `${diffMins}m`;
                              if (diffHours < 24) return `${diffHours}h`;
                              if (diffDays < 7) return `${diffDays}d`;
                              return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
                            };

                            const relativeTime = getRelativeTime(session.updated);

                            return (
                              <Button
                                key={session.id}
                                variant="ghost"
                                className="w-full justify-start h-auto min-h-[36px] px-3 py-2 text-xs font-normal text-muted-foreground hover:bg-accent/50 hover:text-foreground group"
                                onClick={() => handleLoadConversation(session.id)}
                                title={session.preview || session.title}
                              >
                                <div className="flex items-start w-full gap-2">
                                  <Circle className="h-1.5 w-1.5 fill-green-500 text-green-500 mt-1.5 flex-shrink-0" />
                                  <div className="flex flex-col items-start flex-1 min-w-0 gap-0.5">
                                    <div className="flex items-baseline justify-between w-full gap-2">
                                      <span className="truncate text-left flex-1">{displayTitle}</span>
                                      <span className="text-[10px] text-muted-foreground/50 flex-shrink-0 font-mono">{relativeTime}</span>
                                    </div>
                                    <span className="text-[10px] text-muted-foreground/70 font-mono">
                                      {session.message_count} msg{session.message_count !== 1 ? 's' : ''}
                                    </span>
                                  </div>
                                </div>
                              </Button>
                            );
                          })}
                        <Button
                          variant="ghost"
                          className="w-full justify-start h-9 px-4 text-xs font-normal text-primary hover:bg-accent/50"
                          onClick={() => onNavigate('history')}
                        >
                          <History className="h-3 w-3 mr-2" />
                          View All History
                        </Button>
                      </>
                    ) : (
                      <div className="px-4 py-2 text-xs text-muted-foreground">
                        No recent chats
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          }
          
          return (
            <Button
              key={page.id}
              variant="ghost"
              className={`w-full justify-start gap-3 h-11 px-4 text-sm font-normal ${
                currentPage === page.id
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
              }`}
              onClick={() => onNavigate(page.id)}
            >
              <Icon className="h-4 w-4" />
              <span>{page.label}</span>
              {page.experimental && (
                <Badge className="ml-auto bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/20 text-xs">
                  Experimental
                </Badge>
              )}
            </Button>
          );
        })}
      </div>

      <div className="p-4 border-t border-border space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            <Circle className="h-2 w-2 fill-green-500 text-green-500" />
            <span className="text-muted-foreground">All systems operational</span>
          </div>
          <ThemeToggleButton />
        </div>

        {updateAvailable && (
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-start gap-2 text-xs border-green-500/50 bg-green-500/10 text-green-700 dark:text-green-400 hover:bg-green-500/20"
            onClick={() => setUpgradeDialogOpen(true)}
          >
            <Download className="h-3 w-3" />
            <span>Update Available</span>
            <Badge className="ml-auto bg-green-500 text-white text-xs">New</Badge>
          </Button>
        )}

        <div className="flex items-center justify-between">
          <button
            onClick={() => setUpgradeDialogOpen(true)}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            v{currentVersion}
          </button>
          {!updateAvailable && (
            <span className="text-[10px] text-muted-foreground/50">Up to date</span>
          )}
        </div>
      </div>

      <UpgradeDialog
        open={upgradeDialogOpen}
        onOpenChange={setUpgradeDialogOpen}
      />
    </nav>
  );
}
