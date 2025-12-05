/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

/**
 * WebSocket Service
 * Pure WebSocket handling with event emitter pattern
 * No React dependencies - testable and reusable
 */
class WebSocketService {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
    this.ws = null;
    this.handlers = {
      message: [],
      open: [],
      close: [],
      error: [],
    };
  }

  /**
   * Connect to WebSocket endpoint
   */
  connect(endpoint) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.warn('WebSocket already connected');
      return;
    }

    const wsUrl = this.baseUrl.replace('http', 'ws');
    const fullUrl = `${wsUrl}${endpoint}`;

    console.log(`Connecting to WebSocket: ${fullUrl}`);
    this.ws = new WebSocket(fullUrl);

    this.ws.onopen = (event) => {
      console.log('WebSocket connected');
      this._emit('open', event);
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this._emit('message', data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
        this._emit('error', { type: 'parse_error', error, raw: event.data });
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this._emit('error', error);
    };

    this.ws.onclose = (event) => {
      console.log('WebSocket closed', event.code, event.reason);
      this._emit('close', event);
    };
  }

  /**
   * Send data through WebSocket
   */
  send(data) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not connected');
    }

    const message = typeof data === 'string' ? data : JSON.stringify(data);
    this.ws.send(message);
  }

  /**
   * Close WebSocket connection
   */
  close() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Register event handler
   */
  on(event, handler) {
    if (!this.handlers[event]) {
      throw new Error(`Unknown event: ${event}`);
    }

    this.handlers[event].push(handler);

    // Return unsubscribe function
    return () => {
      this.handlers[event] = this.handlers[event].filter(h => h !== handler);
    };
  }

  /**
   * Emit event to all registered handlers
   */
  _emit(event, data) {
    if (!this.handlers[event]) return;

    this.handlers[event].forEach(handler => {
      try {
        handler(data);
      } catch (error) {
        console.error(`Error in ${event} handler:`, error);
      }
    });
  }

  /**
   * Get current connection state
   */
  getState() {
    if (!this.ws) return 'CLOSED';

    switch (this.ws.readyState) {
      case WebSocket.CONNECTING: return 'CONNECTING';
      case WebSocket.OPEN: return 'OPEN';
      case WebSocket.CLOSING: return 'CLOSING';
      case WebSocket.CLOSED: return 'CLOSED';
      default: return 'UNKNOWN';
    }
  }

  /**
   * Check if connected
   */
  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}

export default WebSocketService;
