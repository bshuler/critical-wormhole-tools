/**
 * TypeScript type definitions for @wormhole-tools/spake2
 */

/**
 * SPAKE2 Symmetric implementation for Magic Wormhole
 */
export class SPAKE2_Symmetric {
  constructor(password: Uint8Array, idSymmetric?: Uint8Array);

  /**
   * Generate our SPAKE2 message
   */
  start(): Uint8Array;

  /**
   * Process peer's message and derive shared key
   */
  finish(inboundMessage: Uint8Array): Uint8Array;
}

/**
 * Create SPAKE2 instance for magic-wormhole
 */
export function createSPAKE2(password: string, appId?: string): SPAKE2_Symmetric;

/**
 * Legacy compatibility class
 */
export class SymmetricSPAKE2 {
  constructor(appId: string, passwordHash: Uint8Array, side: string);
  start(): Promise<Uint8Array>;
  finish(peerMessage: Uint8Array): Promise<Uint8Array>;
}

/**
 * Legacy SPAKE2 class
 */
export class SPAKE2 {
  constructor(password: string, idA: string, idB: string, isA?: boolean);
  start(): Promise<Uint8Array>;
  finish(peerMessage: Uint8Array): Promise<Uint8Array>;
}
