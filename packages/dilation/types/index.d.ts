/**
 * TypeScript type definitions for @wormhole-tools/dilation
 */

/**
 * Dilation states
 */
export const DilationState: {
  IDLE: 'idle';
  WAITING: 'waiting';
  WANTING: 'wanting';
  CONNECTING: 'connecting';
  CONNECTED: 'connected';
  RECONNECTING: 'reconnecting';
  FAILED: 'failed';
  STOPPED: 'stopped';
};

/**
 * Dilation message types
 */
export const DilationMessageType: {
  PLEASE: 'please';
  HINTS: 'connection-hints';
  RECONNECT: 'reconnect';
  RECONNECTING: 'reconnecting';
};

/**
 * Subchannel record types
 */
export const RecordType: {
  OPEN: 0x01;
  DATA: 0x02;
  CLOSE: 0x03;
  ACK: 0x04;
};

/**
 * Dilation manager options
 */
export interface DilationOptions {
  mailbox: any; // MailboxClient
  sharedKey: Uint8Array;
  mailboxSide: string;
  peerSide: string;
  iceServers?: RTCConfiguration;
}

/**
 * DilationManager handles the dilation protocol and subchannel multiplexing
 */
export class DilationManager {
  constructor(options: DilationOptions);

  /**
   * Start the dilation process
   */
  dilate(): Promise<void>;

  /**
   * Open a new subchannel to peer
   */
  openSubchannel(protocol: string): Promise<Subchannel>;

  /**
   * Register a listener for incoming subchannels
   */
  listen(protocol: string, callback: (subchannel: Subchannel) => void): void;

  /**
   * Stop listening for a protocol
   */
  unlisten(protocol: string): void;

  /**
   * Check if dilation is connected
   */
  readonly isConnected: boolean;

  /**
   * Close dilation and all subchannels
   */
  close(): Promise<void>;

  /**
   * Event handlers
   */
  onStateChange?: (newState: string, oldState: string) => void;
  onError?: (error: Error) => void;
  onSubchannelOpen?: (subchannel: Subchannel) => void;
}

/**
 * Subchannel - A multiplexed stream over a dilated wormhole
 */
export class Subchannel {
  /**
   * Send data on this subchannel
   */
  send(data: Uint8Array | string): Promise<void>;

  /**
   * Close this subchannel
   */
  close(): Promise<void>;

  /**
   * Read buffered data
   */
  read(): Uint8Array | null;

  /**
   * Check if data is available
   */
  readonly hasData: boolean;

  /**
   * Event handlers
   */
  onData?: (data: Uint8Array) => void;
  onClose?: () => void;
  onError?: (error: Error) => void;
}

/**
 * Create endpoints interface for compatibility
 */
export function createEndpoints(dilationManager: DilationManager): {
  connect: (protocol: string) => SubchannelConnector;
  listen: (protocol: string) => SubchannelListener;
};

/**
 * SubchannelConnector - Creates outgoing subchannel connections
 */
export class SubchannelConnector {
  connect(): Promise<Subchannel>;
}

/**
 * SubchannelListener - Accepts incoming subchannel connections
 */
export class SubchannelListener {
  listen(): Promise<void>;
  accept(): Promise<Subchannel>;
  close(): void;
}

/**
 * NaCl encryption exports
 */
export function encrypt(message: Uint8Array, key: Uint8Array): Promise<Uint8Array>;
export function decrypt(data: Uint8Array, key: Uint8Array): Promise<Uint8Array | null>;
export class NonceCounter {
  next(): Uint8Array;
}
