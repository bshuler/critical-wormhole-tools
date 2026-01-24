/**
 * WebRTC Transit Handler
 *
 * Provides peer-to-peer data channels for wormhole connections.
 * Uses WebRTC for browser-based transit instead of TCP.
 */

import { encrypt, decrypt, NonceCounter } from './nacl.js';

/**
 * ICE server configuration for WebRTC
 */
const DEFAULT_ICE_SERVERS = [
  { urls: 'stun:stun.l.google.com:19302' },
  { urls: 'stun:stun1.l.google.com:19302' }
];

/**
 * Transit connection states
 */
export const TransitState = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  FAILED: 'failed',
  CLOSED: 'closed'
};

/**
 * WebRTC Transit Handler
 *
 * Manages WebRTC peer connections for wormhole data transfer.
 */
export class TransitHandler {
  /**
   * @param {object} options
   * @param {Uint8Array} options.transitKey - Encryption key for data
   * @param {RTCConfiguration} options.iceServers - ICE server config
   */
  constructor(options = {}) {
    this.transitKey = options.transitKey;
    this.iceServers = options.iceServers || DEFAULT_ICE_SERVERS;

    this.peerConnection = null;
    this.dataChannel = null;
    this.state = TransitState.DISCONNECTED;

    // Encryption
    this.sendNonce = new NonceCounter();
    this.receiveNonces = new Set();

    // Handlers
    this.onOpen = null;
    this.onClose = null;
    this.onError = null;
    this.onMessage = null;

    // ICE candidates and offers
    this.localCandidates = [];
    this.pendingRemoteCandidates = [];
  }

  /**
   * Create an offer to connect (initiator)
   * @returns {Promise<{offer: RTCSessionDescriptionInit, candidates: RTCIceCandidateInit[]}>}
   */
  async createOffer() {
    this.state = TransitState.CONNECTING;

    this.peerConnection = new RTCPeerConnection({
      iceServers: this.iceServers
    });

    this.setupPeerConnectionHandlers();

    // Create data channel (only initiator creates channel)
    this.dataChannel = this.peerConnection.createDataChannel('transit', {
      ordered: true
    });
    this.setupDataChannelHandlers(this.dataChannel);

    // Create and set local description
    const offer = await this.peerConnection.createOffer();
    await this.peerConnection.setLocalDescription(offer);

    // Wait for ICE gathering to complete
    await this.waitForIceGathering();

    return {
      offer: this.peerConnection.localDescription,
      candidates: this.localCandidates
    };
  }

  /**
   * Accept an offer and create answer (responder)
   * @param {RTCSessionDescriptionInit} offer
   * @param {RTCIceCandidateInit[]} candidates
   * @returns {Promise<{answer: RTCSessionDescriptionInit, candidates: RTCIceCandidateInit[]}>}
   */
  async acceptOffer(offer, candidates = []) {
    this.state = TransitState.CONNECTING;

    this.peerConnection = new RTCPeerConnection({
      iceServers: this.iceServers
    });

    this.setupPeerConnectionHandlers();

    // Handle incoming data channel (responder receives channel)
    this.peerConnection.ondatachannel = (event) => {
      this.dataChannel = event.channel;
      this.setupDataChannelHandlers(this.dataChannel);
    };

    // Set remote description
    await this.peerConnection.setRemoteDescription(offer);

    // Add remote ICE candidates
    for (const candidate of candidates) {
      await this.peerConnection.addIceCandidate(candidate);
    }

    // Create and set local answer
    const answer = await this.peerConnection.createAnswer();
    await this.peerConnection.setLocalDescription(answer);

    // Wait for ICE gathering
    await this.waitForIceGathering();

    return {
      answer: this.peerConnection.localDescription,
      candidates: this.localCandidates
    };
  }

  /**
   * Complete connection with answer (initiator)
   * @param {RTCSessionDescriptionInit} answer
   * @param {RTCIceCandidateInit[]} candidates
   */
  async completeConnection(answer, candidates = []) {
    await this.peerConnection.setRemoteDescription(answer);

    // Add remote ICE candidates
    for (const candidate of candidates) {
      await this.peerConnection.addIceCandidate(candidate);
    }

    // Add any pending candidates
    for (const candidate of this.pendingRemoteCandidates) {
      await this.peerConnection.addIceCandidate(candidate);
    }
    this.pendingRemoteCandidates = [];
  }

  /**
   * Add a remote ICE candidate
   * @param {RTCIceCandidateInit} candidate
   */
  async addIceCandidate(candidate) {
    if (this.peerConnection && this.peerConnection.remoteDescription) {
      await this.peerConnection.addIceCandidate(candidate);
    } else {
      this.pendingRemoteCandidates.push(candidate);
    }
  }

  /**
   * Set up handlers for peer connection
   */
  setupPeerConnectionHandlers() {
    this.peerConnection.onicecandidate = (event) => {
      if (event.candidate) {
        this.localCandidates.push(event.candidate.toJSON());
      }
    };

    this.peerConnection.oniceconnectionstatechange = () => {
      const state = this.peerConnection.iceConnectionState;

      if (state === 'connected' || state === 'completed') {
        this.state = TransitState.CONNECTED;
      } else if (state === 'failed') {
        this.state = TransitState.FAILED;
        if (this.onError) {
          this.onError(new Error('ICE connection failed'));
        }
      } else if (state === 'closed' || state === 'disconnected') {
        this.state = TransitState.CLOSED;
        if (this.onClose) {
          this.onClose();
        }
      }
    };

    this.peerConnection.onconnectionstatechange = () => {
      if (this.peerConnection.connectionState === 'failed') {
        this.state = TransitState.FAILED;
        if (this.onError) {
          this.onError(new Error('Peer connection failed'));
        }
      }
    };
  }

  /**
   * Set up handlers for data channel
   * @param {RTCDataChannel} channel
   */
  setupDataChannelHandlers(channel) {
    channel.binaryType = 'arraybuffer';

    channel.onopen = () => {
      this.state = TransitState.CONNECTED;
      if (this.onOpen) {
        this.onOpen();
      }
    };

    channel.onclose = () => {
      this.state = TransitState.CLOSED;
      if (this.onClose) {
        this.onClose();
      }
    };

    channel.onerror = (event) => {
      this.state = TransitState.FAILED;
      if (this.onError) {
        this.onError(event.error || new Error('Data channel error'));
      }
    };

    channel.onmessage = async (event) => {
      try {
        const data = new Uint8Array(event.data);
        const decrypted = await this.decryptMessage(data);

        if (decrypted && this.onMessage) {
          this.onMessage(decrypted);
        }
      } catch (e) {
        if (this.onError) {
          this.onError(e);
        }
      }
    };
  }

  /**
   * Wait for ICE gathering to complete
   * @returns {Promise<void>}
   */
  waitForIceGathering() {
    return new Promise((resolve) => {
      if (this.peerConnection.iceGatheringState === 'complete') {
        resolve();
        return;
      }

      const checkState = () => {
        if (this.peerConnection.iceGatheringState === 'complete') {
          this.peerConnection.removeEventListener('icegatheringstatechange', checkState);
          resolve();
        }
      };

      this.peerConnection.addEventListener('icegatheringstatechange', checkState);

      // Timeout after 10 seconds
      setTimeout(() => {
        this.peerConnection.removeEventListener('icegatheringstatechange', checkState);
        resolve();
      }, 10000);
    });
  }

  /**
   * Send encrypted data
   * @param {Uint8Array|string} data
   */
  async send(data) {
    if (!this.dataChannel || this.dataChannel.readyState !== 'open') {
      throw new Error('Data channel not open');
    }

    if (typeof data === 'string') {
      data = new TextEncoder().encode(data);
    }

    const encrypted = await this.encryptMessage(data);
    this.dataChannel.send(encrypted);
  }

  /**
   * Encrypt a message for sending
   * @param {Uint8Array} plaintext
   * @returns {Promise<Uint8Array>}
   */
  async encryptMessage(plaintext) {
    if (!this.transitKey) {
      // No encryption, just send raw
      return plaintext;
    }

    return await encrypt(plaintext, this.transitKey);
  }

  /**
   * Decrypt a received message
   * @param {Uint8Array} ciphertext
   * @returns {Promise<Uint8Array|null>}
   */
  async decryptMessage(ciphertext) {
    if (!this.transitKey) {
      // No encryption, return raw
      return ciphertext;
    }

    return await decrypt(ciphertext, this.transitKey);
  }

  /**
   * Close the connection
   */
  close() {
    if (this.dataChannel) {
      this.dataChannel.close();
      this.dataChannel = null;
    }

    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
    }

    this.state = TransitState.CLOSED;
  }

  /**
   * Check if connected
   * @returns {boolean}
   */
  get isConnected() {
    return this.state === TransitState.CONNECTED &&
           this.dataChannel &&
           this.dataChannel.readyState === 'open';
  }
}

/**
 * Create transit hints from WebRTC offer/answer
 * @param {RTCSessionDescriptionInit} description
 * @param {RTCIceCandidateInit[]} candidates
 * @returns {object}
 */
export function createTransitHints(description, candidates) {
  return {
    type: 'webrtc',
    sdp: description.sdp,
    sdpType: description.type,
    candidates: candidates.map(c => ({
      candidate: c.candidate,
      sdpMid: c.sdpMid,
      sdpMLineIndex: c.sdpMLineIndex
    }))
  };
}

/**
 * Parse transit hints from peer
 * @param {object} hints
 * @returns {{description: RTCSessionDescriptionInit, candidates: RTCIceCandidateInit[]}|null}
 */
export function parseTransitHints(hints) {
  if (!hints || hints.type !== 'webrtc') {
    return null;
  }

  return {
    description: {
      type: hints.sdpType,
      sdp: hints.sdp
    },
    candidates: hints.candidates || []
  };
}

/**
 * Exchange transit hints via mailbox
 * @param {MailboxClient} mailbox
 * @param {boolean} isInitiator
 * @param {TransitHandler} transit
 * @returns {Promise<void>}
 */
export async function negotiateTransit(mailbox, isInitiator, transit) {
  if (isInitiator) {
    // Create and send offer
    const { offer, candidates } = await transit.createOffer();
    const hints = createTransitHints(offer, candidates);
    await mailbox.addMessage('transit', JSON.stringify(hints));

    // Wait for answer
    const answerJson = await mailbox.waitForPhase('transit');
    const answerHints = parseTransitHints(JSON.parse(answerJson));

    if (!answerHints) {
      throw new Error('Invalid transit hints from peer');
    }

    await transit.completeConnection(answerHints.description, answerHints.candidates);
  } else {
    // Wait for offer
    const offerJson = await mailbox.waitForPhase('transit');
    const offerHints = parseTransitHints(JSON.parse(offerJson));

    if (!offerHints) {
      throw new Error('Invalid transit hints from peer');
    }

    // Accept and send answer
    const { answer, candidates } = await transit.acceptOffer(
      offerHints.description,
      offerHints.candidates
    );

    const hints = createTransitHints(answer, candidates);
    await mailbox.addMessage('transit', JSON.stringify(hints));
  }
}
