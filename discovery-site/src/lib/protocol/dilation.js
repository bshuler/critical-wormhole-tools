/**
 * Dilation Manager for Browser Extension
 *
 * Implements the Magic Wormhole dilation protocol to enable persistent,
 * multiplexed streaming connections over WebRTC data channels.
 *
 * Dilation transforms a simple message-exchange wormhole into a full
 * streaming connection with:
 * - Multiple independent subchannels
 * - Connection durability (survives network changes)
 * - Efficient bulk data transfer
 *
 * Protocol Flow:
 * 1. Both sides call dilate() after wormhole connection established
 * 2. Exchange PLEASE messages via mailbox to agree on version and roles
 * 3. Exchange CONNECTION-HINTS with WebRTC offers/answers
 * 4. Establish direct WebRTC connection
 * 5. Multiplex subchannels over the encrypted data channel
 */

import { encrypt, decrypt, NonceCounter } from '../crypto/nacl.js';
import { derivePhaseKey } from '../crypto/hkdf.js';

/**
 * Dilation states
 */
export const DilationState = {
  IDLE: 'idle',
  WAITING: 'waiting',       // Called dilate(), waiting for peer
  WANTING: 'wanting',       // Received peer's PLEASE, negotiating
  CONNECTING: 'connecting', // Establishing WebRTC connection
  CONNECTED: 'connected',   // Dilation active
  RECONNECTING: 'reconnecting',
  FAILED: 'failed',
  STOPPED: 'stopped'
};

/**
 * Dilation message types (sent via mailbox as 'dilate-*' phases)
 */
export const DilationMessageType = {
  PLEASE: 'please',
  HINTS: 'connection-hints',
  RECONNECT: 'reconnect',
  RECONNECTING: 'reconnecting'
};

/**
 * Subchannel record types for multiplexing
 */
export const RecordType = {
  OPEN: 0x01,
  DATA: 0x02,
  CLOSE: 0x03,
  ACK: 0x04
};

/**
 * Default ICE servers for WebRTC
 */
const DEFAULT_ICE_SERVERS = [
  { urls: 'stun:stun.l.google.com:19302' },
  { urls: 'stun:stun1.l.google.com:19302' },
  { urls: 'stun:stun2.l.google.com:19302' },
  { urls: 'stun:stun3.l.google.com:19302' },
  { urls: 'stun:stun4.l.google.com:19302' }
];

/**
 * Dilation protocol version supported by this implementation
 */
const DILATION_VERSION = 1;

/**
 * Generate a random dilation side identifier
 * @returns {string}
 */
function generateDilationSide() {
  const bytes = new Uint8Array(8);
  crypto.getRandomValues(bytes);
  return Array.from(bytes)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * DilationManager handles the dilation protocol and subchannel multiplexing
 */
export class DilationManager {
  /**
   * @param {object} options
   * @param {MailboxClient} options.mailbox - Connected mailbox client
   * @param {Uint8Array} options.sharedKey - SPAKE2 shared key
   * @param {string} options.mailboxSide - Our mailbox side identifier
   * @param {string} options.peerSide - Peer's mailbox side identifier
   * @param {RTCConfiguration} options.iceServers - ICE server config
   */
  constructor(options = {}) {
    this.mailbox = options.mailbox;
    this.sharedKey = options.sharedKey;
    this.mailboxSide = options.mailboxSide;
    this.peerSide = options.peerSide;
    this.iceServers = options.iceServers || DEFAULT_ICE_SERVERS;

    // Dilation state
    this.state = DilationState.IDLE;
    this.dilationSide = null;
    this.peerDilationSide = null;
    this.isLeader = false;
    this.generation = 0;

    // WebRTC components
    this.peerConnection = null;
    this.controlChannel = null;  // Primary data channel for control + multiplexing
    this.localCandidates = [];

    // Subchannel management
    this.subchannels = new Map();  // id -> Subchannel
    this.subchannelListeners = new Map();  // protocol -> listener callback
    this.nextSubchannelId = 1;

    // Encryption
    this.dilationKey = null;
    this.sendNonce = new NonceCounter();
    this.receiveNonces = new Set();

    // Message tracking
    this.dilationPhase = 0;
    this.pendingHints = null;

    // Event handlers
    this.onStateChange = null;
    this.onError = null;
    this.onSubchannelOpen = null;

    // Mailbox message handler
    this._messageHandler = null;
  }

  /**
   * Start the dilation process
   * @returns {Promise<void>}
   */
  async dilate() {
    if (this.state !== DilationState.IDLE) {
      throw new Error(`Cannot dilate in state: ${this.state}`);
    }

    console.log('[Dilation] Starting dilation');
    this.setState(DilationState.WAITING);

    // Generate our dilation side identifier
    this.dilationSide = generateDilationSide();
    console.log('[Dilation] Our dilation side:', this.dilationSide);

    // Derive dilation-specific key from shared key
    this.dilationKey = await derivePhaseKey(this.sharedKey, 'dilation', 'key');

    // Start listening for dilation messages
    this._startDilationMessageHandler();

    // Send PLEASE message
    await this._sendDilationMessage({
      type: DilationMessageType.PLEASE,
      side: this.dilationSide,
      'use-version': DILATION_VERSION
    });

    // Wait for connection to be established
    return this._waitForConnection();
  }

  /**
   * Wait for dilation connection to complete
   * @returns {Promise<void>}
   */
  _waitForConnection() {
    return new Promise((resolve, reject) => {
      const checkState = () => {
        if (this.state === DilationState.CONNECTED) {
          resolve();
        } else if (this.state === DilationState.FAILED || this.state === DilationState.STOPPED) {
          reject(new Error('Dilation failed'));
        }
      };

      // Check immediately
      checkState();

      // Set up state change listener
      const originalHandler = this.onStateChange;
      this.onStateChange = (newState, oldState) => {
        if (originalHandler) originalHandler(newState, oldState);
        checkState();
      };

      // Timeout after 30 seconds to allow time for server-side dilation
      setTimeout(() => {
        if (this.state !== DilationState.CONNECTED) {
          this.setState(DilationState.FAILED);
          reject(new Error('Dilation timeout'));
        }
      }, 30000);
    });
  }

  /**
   * Start handling dilation messages from mailbox
   */
  _startDilationMessageHandler() {
    this._messageHandler = this.mailbox.onMessage((phase, body, side) => {
      // Dilation messages use 'dilate-N' phase naming
      if (!phase.startsWith('dilate-')) return;

      console.log('[Dilation] Received dilation message, phase:', phase);

      // Decrypt and parse
      this._handleDilationMessage(body, side);
    });
  }

  /**
   * Handle incoming dilation message
   * @param {Uint8Array|string} body
   * @param {string} side
   */
  async _handleDilationMessage(body, side) {
    try {
      // Decrypt if binary
      let message;
      if (body instanceof Uint8Array) {
        const decrypted = await decrypt(body, this.dilationKey);
        message = JSON.parse(new TextDecoder().decode(decrypted));
      } else {
        message = JSON.parse(body);
      }

      console.log('[Dilation] Parsed message:', message.type);

      switch (message.type) {
        case DilationMessageType.PLEASE:
          await this._handlePlease(message);
          break;
        case DilationMessageType.HINTS:
          await this._handleHints(message);
          break;
        case DilationMessageType.RECONNECT:
          await this._handleReconnect(message);
          break;
        case DilationMessageType.RECONNECTING:
          await this._handleReconnecting(message);
          break;
        default:
          console.warn('[Dilation] Unknown message type:', message.type);
      }
    } catch (e) {
      console.error('[Dilation] Error handling message:', e);
    }
  }

  /**
   * Handle PLEASE message from peer
   * @param {object} message
   */
  async _handlePlease(message) {
    console.log('[Dilation] Received PLEASE from peer');
    this.peerDilationSide = message.side;

    // Determine leader/follower based on side comparison
    // Higher side becomes leader
    this.isLeader = this.dilationSide > this.peerDilationSide;
    console.log('[Dilation] Role:', this.isLeader ? 'Leader' : 'Follower');

    this.setState(DilationState.WANTING);

    // Start WebRTC connection
    await this._startWebRTC();
  }

  /**
   * Handle CONNECTION-HINTS message from peer
   * @param {object} message
   */
  async _handleHints(message) {
    console.log('[Dilation] Received connection hints');

    if (!message.hints || !message.hints.webrtc) {
      console.warn('[Dilation] No WebRTC hints in message');
      return;
    }

    const hints = message.hints.webrtc;

    if (this.isLeader) {
      // Leader receives answer
      if (hints.type === 'answer') {
        await this._handleWebRTCAnswer(hints);
      }
    } else {
      // Follower receives offer
      if (hints.type === 'offer') {
        await this._handleWebRTCOffer(hints);
      }
    }
  }

  /**
   * Handle RECONNECT message (sent by leader)
   */
  async _handleReconnect(message) {
    console.log('[Dilation] Received RECONNECT');
    // TODO: Implement reconnection
  }

  /**
   * Handle RECONNECTING message (sent by follower)
   */
  async _handleReconnecting(message) {
    console.log('[Dilation] Received RECONNECTING');
    // TODO: Implement reconnection
  }

  /**
   * Start WebRTC connection based on role
   */
  async _startWebRTC() {
    this.setState(DilationState.CONNECTING);

    this.peerConnection = new RTCPeerConnection({
      iceServers: this.iceServers
    });

    this._setupPeerConnectionHandlers();

    if (this.isLeader) {
      // Leader creates offer
      await this._createOffer();
    }
    // Follower waits for offer in hints
  }

  /**
   * Set up WebRTC peer connection event handlers
   */
  _setupPeerConnectionHandlers() {
    this.peerConnection.onicecandidate = (event) => {
      if (event.candidate) {
        this.localCandidates.push(event.candidate.toJSON());
      }
    };

    this.peerConnection.onicegatheringstatechange = () => {
      if (this.peerConnection.iceGatheringState === 'complete') {
        console.log('[Dilation] ICE gathering complete');
        // Send hints with complete candidates
        if (this.pendingHints) {
          this._sendHints(this.pendingHints);
          this.pendingHints = null;
        }
      }
    };

    this.peerConnection.oniceconnectionstatechange = () => {
      const state = this.peerConnection.iceConnectionState;
      console.log('[Dilation] ICE connection state:', state);

      if (state === 'connected' || state === 'completed') {
        // Connection established but wait for data channel
      } else if (state === 'failed') {
        this.setState(DilationState.FAILED);
        if (this.onError) {
          this.onError(new Error('ICE connection failed'));
        }
      } else if (state === 'disconnected') {
        this.setState(DilationState.RECONNECTING);
      }
    };

    this.peerConnection.ondatachannel = (event) => {
      console.log('[Dilation] Received data channel:', event.channel.label);
      if (event.channel.label === 'dilation-control') {
        this.controlChannel = event.channel;
        this._setupControlChannel();
      }
    };
  }

  /**
   * Create WebRTC offer (leader only)
   */
  async _createOffer() {
    // Create control channel (only leader creates it)
    this.controlChannel = this.peerConnection.createDataChannel('dilation-control', {
      ordered: true,
      protocol: 'wormhole-dilation'
    });
    this._setupControlChannel();

    const offer = await this.peerConnection.createOffer();
    await this.peerConnection.setLocalDescription(offer);

    // Wait for ICE gathering to complete before sending
    await this._waitForIceGathering();

    // Send hints
    await this._sendHints({
      type: 'offer',
      sdp: this.peerConnection.localDescription.sdp,
      candidates: this.localCandidates
    });
  }

  /**
   * Handle WebRTC offer from leader (follower only)
   */
  async _handleWebRTCOffer(hints) {
    console.log('[Dilation] Processing WebRTC offer');

    await this.peerConnection.setRemoteDescription({
      type: 'offer',
      sdp: hints.sdp
    });

    // Add ICE candidates
    if (hints.candidates) {
      for (const candidate of hints.candidates) {
        await this.peerConnection.addIceCandidate(candidate);
      }
    }

    // Create answer
    const answer = await this.peerConnection.createAnswer();
    await this.peerConnection.setLocalDescription(answer);

    // Wait for ICE gathering
    await this._waitForIceGathering();

    // Send answer hints
    await this._sendHints({
      type: 'answer',
      sdp: this.peerConnection.localDescription.sdp,
      candidates: this.localCandidates
    });
  }

  /**
   * Handle WebRTC answer from follower (leader only)
   */
  async _handleWebRTCAnswer(hints) {
    console.log('[Dilation] Processing WebRTC answer');

    await this.peerConnection.setRemoteDescription({
      type: 'answer',
      sdp: hints.sdp
    });

    // Add ICE candidates
    if (hints.candidates) {
      for (const candidate of hints.candidates) {
        await this.peerConnection.addIceCandidate(candidate);
      }
    }
  }

  /**
   * Wait for ICE gathering to complete
   */
  _waitForIceGathering() {
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
   * Set up the control data channel
   */
  _setupControlChannel() {
    this.controlChannel.binaryType = 'arraybuffer';

    this.controlChannel.onopen = () => {
      console.log('[Dilation] Control channel open');
      this.setState(DilationState.CONNECTED);
    };

    this.controlChannel.onclose = () => {
      console.log('[Dilation] Control channel closed');
      if (this.state === DilationState.CONNECTED) {
        this.setState(DilationState.RECONNECTING);
      }
    };

    this.controlChannel.onerror = (event) => {
      console.error('[Dilation] Control channel error:', event);
      if (this.onError) {
        this.onError(event.error || new Error('Control channel error'));
      }
    };

    this.controlChannel.onmessage = (event) => {
      this._handleControlMessage(new Uint8Array(event.data));
    };
  }

  /**
   * Handle incoming message on control channel
   * @param {Uint8Array} data
   */
  async _handleControlMessage(data) {
    try {
      // Decrypt message
      const decrypted = await decrypt(data, this.dilationKey);
      if (!decrypted) {
        console.warn('[Dilation] Failed to decrypt control message');
        return;
      }

      // Parse record
      const record = this._parseRecord(decrypted);
      if (!record) return;

      const subchannel = this.subchannels.get(record.id);

      switch (record.type) {
        case RecordType.OPEN:
          await this._handleSubchannelOpen(record);
          break;
        case RecordType.DATA:
          if (subchannel) {
            subchannel._receiveData(record.data);
          }
          break;
        case RecordType.CLOSE:
          if (subchannel) {
            subchannel._handleClose(record.data);
          }
          break;
        case RecordType.ACK:
          if (subchannel) {
            subchannel._handleAck(record.seqnum);
          }
          break;
      }
    } catch (e) {
      console.error('[Dilation] Error handling control message:', e);
    }
  }

  /**
   * Parse a subchannel record
   * @param {Uint8Array} data
   * @returns {object|null}
   */
  _parseRecord(data) {
    if (data.length < 5) return null;

    const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
    const type = data[0];
    const id = view.getUint32(1, false);  // Big-endian subchannel ID

    return {
      type,
      id,
      data: data.slice(5),
      seqnum: type === RecordType.ACK ? view.getUint32(5, false) : null
    };
  }

  /**
   * Handle subchannel open request
   * @param {object} record
   */
  async _handleSubchannelOpen(record) {
    // Parse protocol name from data
    const protocol = new TextDecoder().decode(record.data);
    console.log('[Dilation] Subchannel open request:', record.id, 'protocol:', protocol);

    // Check if we have a listener for this protocol
    const listener = this.subchannelListeners.get(protocol);
    if (!listener) {
      console.warn('[Dilation] No listener for protocol:', protocol);
      // Send close
      await this._sendRecord(RecordType.CLOSE, record.id, new Uint8Array([0]));
      return;
    }

    // Create subchannel
    const subchannel = new Subchannel(this, record.id, protocol, false);
    this.subchannels.set(record.id, subchannel);

    // Notify listener
    listener(subchannel);

    if (this.onSubchannelOpen) {
      this.onSubchannelOpen(subchannel);
    }
  }

  /**
   * Send a dilation message via mailbox
   * @param {object} message
   */
  async _sendDilationMessage(message) {
    const phase = `dilate-${this.dilationPhase++}`;
    const data = new TextEncoder().encode(JSON.stringify(message));
    const encrypted = await encrypt(data, this.dilationKey);

    await this.mailbox.addMessage(phase, encrypted);
  }

  /**
   * Send connection hints
   * @param {object} webrtcHints
   */
  async _sendHints(webrtcHints) {
    await this._sendDilationMessage({
      type: DilationMessageType.HINTS,
      hints: {
        webrtc: webrtcHints
      }
    });
  }

  /**
   * Send a record on the control channel
   * @param {number} type
   * @param {number} id
   * @param {Uint8Array} data
   */
  async _sendRecord(type, id, data = new Uint8Array(0)) {
    if (!this.controlChannel || this.controlChannel.readyState !== 'open') {
      throw new Error('Control channel not open');
    }

    // Build record: type (1) + id (4) + data
    const record = new Uint8Array(5 + data.length);
    record[0] = type;
    new DataView(record.buffer).setUint32(1, id, false);  // Big-endian
    record.set(data, 5);

    // Encrypt and send
    const encrypted = await encrypt(record, this.dilationKey);
    this.controlChannel.send(encrypted);
  }

  /**
   * Open a new subchannel to peer
   * @param {string} protocol - Protocol name (e.g., 'wh-http')
   * @returns {Promise<Subchannel>}
   */
  async openSubchannel(protocol) {
    if (this.state !== DilationState.CONNECTED) {
      throw new Error('Dilation not connected');
    }

    const id = this.nextSubchannelId++;
    const subchannel = new Subchannel(this, id, protocol, true);
    this.subchannels.set(id, subchannel);

    // Send open request
    const protocolBytes = new TextEncoder().encode(protocol);
    await this._sendRecord(RecordType.OPEN, id, protocolBytes);

    console.log('[Dilation] Opened subchannel:', id, 'protocol:', protocol);
    return subchannel;
  }

  /**
   * Register a listener for incoming subchannels
   * @param {string} protocol - Protocol to listen for
   * @param {function} callback - Called with (subchannel) when connection received
   */
  listen(protocol, callback) {
    this.subchannelListeners.set(protocol, callback);
    console.log('[Dilation] Listening for protocol:', protocol);
  }

  /**
   * Stop listening for a protocol
   * @param {string} protocol
   */
  unlisten(protocol) {
    this.subchannelListeners.delete(protocol);
  }

  /**
   * Update state and notify
   * @param {string} newState
   */
  setState(newState) {
    const oldState = this.state;
    this.state = newState;
    console.log('[Dilation] State:', oldState, '->', newState);

    if (this.onStateChange && oldState !== newState) {
      this.onStateChange(newState, oldState);
    }
  }

  /**
   * Check if dilation is connected
   * @returns {boolean}
   */
  get isConnected() {
    return this.state === DilationState.CONNECTED &&
           this.controlChannel &&
           this.controlChannel.readyState === 'open';
  }

  /**
   * Close dilation and all subchannels
   */
  async close() {
    console.log('[Dilation] Closing');

    // Close all subchannels
    for (const subchannel of this.subchannels.values()) {
      subchannel.close();
    }
    this.subchannels.clear();

    // Remove mailbox handler
    if (this._messageHandler) {
      this._messageHandler();
      this._messageHandler = null;
    }

    // Close WebRTC
    if (this.controlChannel) {
      this.controlChannel.close();
      this.controlChannel = null;
    }

    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
    }

    this.setState(DilationState.STOPPED);
  }
}

/**
 * Subchannel - A multiplexed stream over a dilated wormhole
 */
export class Subchannel {
  /**
   * @param {DilationManager} manager
   * @param {number} id
   * @param {string} protocol
   * @param {boolean} isInitiator
   */
  constructor(manager, id, protocol, isInitiator) {
    this.manager = manager;
    this.id = id;
    this.protocol = protocol;
    this.isInitiator = isInitiator;

    this.isOpen = true;
    this.sendSeqnum = 0;
    this.recvSeqnum = 0;

    // Buffered data
    this.receiveBuffer = [];

    // Event handlers
    this.onData = null;
    this.onClose = null;
    this.onError = null;
  }

  /**
   * Send data on this subchannel
   * @param {Uint8Array|string} data
   */
  async send(data) {
    if (!this.isOpen) {
      throw new Error('Subchannel closed');
    }

    if (typeof data === 'string') {
      data = new TextEncoder().encode(data);
    }

    await this.manager._sendRecord(RecordType.DATA, this.id, data);
    this.sendSeqnum++;
  }

  /**
   * Receive data (internal)
   * @param {Uint8Array} data
   */
  _receiveData(data) {
    this.recvSeqnum++;

    if (this.onData) {
      this.onData(data);
    } else {
      this.receiveBuffer.push(data);
    }
  }

  /**
   * Handle close from peer
   */
  _handleClose(data) {
    this.isOpen = false;
    this.manager.subchannels.delete(this.id);

    if (this.onClose) {
      this.onClose();
    }
  }

  /**
   * Handle ACK from peer
   */
  _handleAck(seqnum) {
    // For flow control - not implemented yet
  }

  /**
   * Close this subchannel
   */
  async close() {
    if (!this.isOpen) return;

    this.isOpen = false;

    try {
      await this.manager._sendRecord(RecordType.CLOSE, this.id, new Uint8Array([0]));
    } catch (e) {
      // Ignore errors during close
    }

    this.manager.subchannels.delete(this.id);
  }

  /**
   * Read buffered data
   * @returns {Uint8Array|null}
   */
  read() {
    return this.receiveBuffer.shift() || null;
  }

  /**
   * Check if data is available
   * @returns {boolean}
   */
  get hasData() {
    return this.receiveBuffer.length > 0;
  }
}

/**
 * Create endpoints interface for compatibility with Python API
 */
export function createEndpoints(dilationManager) {
  return {
    /**
     * Get a connector endpoint for outgoing connections
     * @param {string} protocol
     * @returns {SubchannelConnector}
     */
    connect: (protocol) => new SubchannelConnector(dilationManager, protocol),

    /**
     * Get a listener endpoint for incoming connections
     * @param {string} protocol
     * @returns {SubchannelListener}
     */
    listen: (protocol) => new SubchannelListener(dilationManager, protocol)
  };
}

/**
 * SubchannelConnector - Creates outgoing subchannel connections
 */
class SubchannelConnector {
  constructor(manager, protocol) {
    this.manager = manager;
    this.protocol = protocol;
  }

  /**
   * Connect to peer's listener for this protocol
   * @returns {Promise<Subchannel>}
   */
  async connect() {
    return this.manager.openSubchannel(this.protocol);
  }
}

/**
 * SubchannelListener - Accepts incoming subchannel connections
 */
class SubchannelListener {
  constructor(manager, protocol) {
    this.manager = manager;
    this.protocol = protocol;
    this._pendingConnections = [];
    this._waitingResolvers = [];
  }

  /**
   * Start listening for connections
   * @returns {Promise<void>}
   */
  async listen() {
    this.manager.listen(this.protocol, (subchannel) => {
      if (this._waitingResolvers.length > 0) {
        const resolve = this._waitingResolvers.shift();
        resolve(subchannel);
      } else {
        this._pendingConnections.push(subchannel);
      }
    });
  }

  /**
   * Accept an incoming connection
   * @returns {Promise<Subchannel>}
   */
  async accept() {
    if (this._pendingConnections.length > 0) {
      return this._pendingConnections.shift();
    }

    return new Promise((resolve) => {
      this._waitingResolvers.push(resolve);
    });
  }

  /**
   * Stop listening
   */
  close() {
    this.manager.unlisten(this.protocol);
  }
}
