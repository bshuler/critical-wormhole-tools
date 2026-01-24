/**
 * TypeScript type definitions for @wormhole-tools/mailbox
 */

/**
 * Mailbox message types
 */
export const MessageType: {
  BIND: 'bind';
  ALLOCATE: 'allocate';
  CLAIM: 'claim';
  OPEN: 'open';
  ADD: 'add';
  RELEASE: 'release';
  CLOSE: 'close';
  PING: 'ping';
  WELCOME: 'welcome';
  ALLOCATED: 'allocated';
  CLAIMED: 'claimed';
  MESSAGE: 'message';
  RELEASED: 'released';
  CLOSED: 'closed';
  ACK: 'ack';
  PONG: 'pong';
  ERROR: 'error';
};

/**
 * Default relay server
 */
export const DEFAULT_RELAY: string;

/**
 * Mailbox client for wormhole rendezvous
 */
export class MailboxClient {
  constructor(relayUrl?: string, appId?: string);

  /**
   * Generate a unique side identifier
   */
  static generateSide(): string;

  /**
   * Connect to the relay server
   */
  connect(): Promise<object>;

  /**
   * Allocate a new nameplate
   */
  allocate(): Promise<string>;

  /**
   * Claim an existing nameplate
   */
  claim(nameplate: string): Promise<object>;

  /**
   * Open the mailbox for message exchange
   */
  open(mailbox?: string): Promise<void>;

  /**
   * Add a message to the mailbox
   */
  addMessage(phase: string, body: string | object | Uint8Array): Promise<void>;

  /**
   * Register a handler for incoming messages
   */
  onMessage(handler: (phase: string, body: string | Uint8Array, side: string) => void): () => void;

  /**
   * Wait for a specific phase message from peer
   */
  waitForPhase(phase: string, timeout?: number): Promise<string | Uint8Array>;

  /**
   * Wait for a specific phase message from peer, returning both body and sender's side
   */
  waitForPhaseWithSide(phase: string, timeout?: number): Promise<{ body: string | Uint8Array; side: string }>;

  /**
   * Release the nameplate
   */
  release(): Promise<void>;

  /**
   * Close the mailbox and disconnect
   */
  close(): Promise<void>;

  /**
   * Our side identifier
   */
  side: string | null;
}

/**
 * Parse a wormhole code into nameplate and password
 */
export function parseCode(code: string): { nameplate: string; password: string };

/**
 * Generate a wormhole code
 */
export function generateCode(nameplate: string, numWords?: number): string;
