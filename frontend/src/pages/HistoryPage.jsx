/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { MessageSquare, Search, RefreshCw } from 'lucide-react';
import { useConversationHistoryContext } from '../contexts/ConversationHistoryContext';

export default function HistoryPage({ onNavigate }) {
  const { sessions, loadSessions, loadSession, searchMessages } = useConversationHistoryContext();
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredSessions, setFilteredSessions] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [searching, setSearching] = useState(false);
  const conversationsPerPage = 20;

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  useEffect(() => {
    const performSearch = async () => {
      if (searchQuery.trim()) {
        setSearching(true);
        try {
          // Search message content via backend
          const results = await searchMessages(searchQuery);

          // Extract unique session IDs from search results
          const matchedSessionIds = new Set(
            results.map(r => r.session_id)
          );

          // Filter sessions to only those with matching messages
          setFilteredSessions(
            sessions.filter(s => matchedSessionIds.has(s.id))
          );
        } catch (err) {
          console.error('[HistoryPage] Search error:', err);
          // Fallback to title-only search
          setFilteredSessions(
            sessions.filter(s =>
              s.title.toLowerCase().includes(searchQuery.toLowerCase())
            )
          );
        } finally {
          setSearching(false);
        }
      } else {
        setFilteredSessions(sessions);
      }
      // Reset to first page when search changes
      setCurrentPage(1);
    };

    performSearch();
  }, [searchQuery, sessions, searchMessages]);

  // Bounds check: reset to page 1 if currentPage exceeds totalPages
  useEffect(() => {
    const nonEmpty = filteredSessions.filter(s => s.message_count > 0);
    const total = conversationsPerPage > 0
      ? Math.ceil(nonEmpty.length / conversationsPerPage)
      : 0;
    if (currentPage > total && total > 0) {
      setCurrentPage(1);
    }
  }, [filteredSessions, currentPage, conversationsPerPage]);

  const handleLoadConversation = async (sessionId) => {
    await loadSession(sessionId);
    onNavigate('playground');
  };

  // Calculate pagination
  const nonEmptySessions = filteredSessions.filter(s => s.message_count > 0);
  const totalPages = conversationsPerPage > 0
    ? Math.ceil(nonEmptySessions.length / conversationsPerPage)
    : 0;
  const startIndex = (currentPage - 1) * conversationsPerPage;
  const endIndex = startIndex + conversationsPerPage;
  const paginatedSessions = nonEmptySessions.slice(startIndex, endIndex);

  return (
    <div className="h-screen bg-background p-6">
      <div className="max-w-5xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-foreground mb-2">Conversation History</h1>
          <p className="text-muted-foreground">View and manage all your conversations</p>
        </div>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>All Conversations</CardTitle>
                <CardDescription>
                  {searching ? 'Searching...' : (
                    <>
                      {nonEmptySessions.length} conversations
                      {totalPages > 1 && ` (Page ${currentPage} of ${totalPages})`}
                    </>
                  )}
                </CardDescription>
              </div>
              <Button size="sm" variant="outline" onClick={loadSessions}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            </div>
            <div className="relative mt-4">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[600px]">
              {filteredSessions.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No conversations found</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {paginatedSessions.map(session => (
                    <div
                      key={session.id}
                      className="flex items-center justify-between p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors cursor-pointer"
                      onClick={() => handleLoadConversation(session.id)}
                    >
                      <div className="flex-1">
                        <h3 className="font-medium text-foreground truncate" title={session.title}>{session.title}</h3>
                        <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
                          <span>{session.message_count} messages</span>
                          <span>•</span>
                          <span>{new Date(session.created).toLocaleDateString()}</span>
                        </div>
                      </div>
                      <Badge variant="outline">{session.status}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 p-4 border-t">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                >
                  Previous
                </Button>
                <span className="text-sm text-muted-foreground px-4">
                  Page {currentPage} of {totalPages}
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage >= totalPages || totalPages === 0}
                >
                  Next
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
