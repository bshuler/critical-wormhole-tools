/**
 * TypeScript type definitions for @wormhole-tools/protocol
 */

/**
 * Wormhole connection states
 */
export const WormholeState: {
  DISCONNECTED: 'disconnected';
  ALLOCATING: 'allocating';
  WAITING: 'waiting';
  EXCHANGING: 'exchanging';
  CONNECTED: 'connected';
  DILATING: 'dilating';
  DILATED: 'dilated';
  FAILED: 'failed';
  CLOSED: 'closed';
};

/**
 * Wormhole options
 */
export interface WormholeOptions {
  relayUrl?: string;
  appId?: string;
}

/**
 * Wormhole connection
 */
export class Wormhole {
  constructor(options?: WormholeOptions);

  /**
   * Create a new wormhole code (sender side)
   */
  allocate(numWords?: number): Promise<string>;

  /**
   * Connect using an existing code (receiver side)
   */
  connect(code: string): Promise<void>;

  /**
   * Wait for peer to connect and complete handshake (sender side)
   */
  waitForPeer(): Promise<void>;

  /**
   * Send data to peer
   */
  send(data: Uint8Array | string): Promise<void>;

  /**
   * Receive data (for mailbox-based transfer)
   */
  receive(timeout?: number): Promise<Uint8Array>;

  /**
   * Send a file to peer
   */
  sendFile(file: File | Blob, onProgress?: (received: number, total: number) => void): Promise<void>;

  /**
   * Dilate the wormhole for streaming communication
   */
  dilate(): Promise<{
    connect: (protocol: string) => any; // SubchannelConnector
    listen: (protocol: string) => any;  // SubchannelListener
  }>;

  /**
   * Check if wormhole is dilated
   */
  readonly isDilated: boolean;

  /**
   * Close the connection
   */
  close(): Promise<void>;

  /**
   * The wormhole code
   */
  code: string | null;

  /**
   * Current state
   */
  state: string;

  /**
   * Verifier for code confirmation
   */
  verifier: string | null;

  /**
   * Event handlers
   */
  onStateChange?: (newState: string, oldState: string) => void;
  onMessage?: (data: Uint8Array) => void;
  onError?: (error: Error) => void;
  onDilationStateChange?: (newState: string, oldState: string) => void;
}

/**
 * Create a wormhole and allocate a code (sender)
 */
export function createWormhole(options?: WormholeOptions): Promise<Wormhole>;

/**
 * Connect to a wormhole using a code (receiver)
 */
export function connectWormhole(code: string, options?: WormholeOptions): Promise<Wormhole>;

/**
 * Transit handler exports
 */
export class TransitHandler {
  constructor(options: { transitKey: Uint8Array; iceServers?: RTCConfiguration });
  send(data: Uint8Array | string): Promise<void>;
  close(): void;
  readonly isConnected: boolean;
}

export function negotiateTransit(mailbox: any, isInitiator: boolean, transit: TransitHandler): Promise<void>;
