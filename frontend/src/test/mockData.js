/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

export const mockSessions = [
  {
    id: 'session-1',
    title: 'Test Conversation 1',
    message_count: 5,
    created: '2025-11-01T10:00:00Z',
    updated: '2025-11-01T10:30:00Z',
    status: 'active'
  },
  {
    id: 'session-2',
    title: 'Test Conversation 2',
    message_count: 3,
    created: '2025-11-01T09:00:00Z',
    updated: '2025-11-01T09:30:00Z',
    status: 'active'
  },
  {
    id: 'session-3',
    title: 'Security Scan Discussion',
    message_count: 10,
    created: '2025-11-01T08:00:00Z',
    updated: '2025-11-01T08:30:00Z',
    status: 'active'
  }
];

export const mockMessages = [
  {
    id: 1,
    role: 'user',
    content: 'Hello',
    timestamp: '2025-11-01T10:00:00Z'
  },
  {
    id: 2,
    role: 'assistant',
    content: 'Hi there!',
    timestamp: '2025-11-01T10:00:05Z',
    agent: 'agent'
  }
];

export const mockTeams = [
  {
    id: 'team-1',
    name: 'Default Agent',
    description: 'General purpose AI agent',
    agents: [{ name: 'agent', role: 'assistant' }]
  }
];
