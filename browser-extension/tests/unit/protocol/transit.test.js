/**
 * Unit tests for Transit Handler
 *
 * Tests the WebRTC transit implementation for browser extension.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock WebRTC APIs before importing transit
const mockDataChannel = {
  binaryType: 'arraybuffer',
  readyState: 'connecting',
  send: vi.fn(),
  close: vi.fn(),
  onopen: null,
  onclose: null,
  onerror: null,
  onmessage: null
};

const mockPeerConnection = {
  localDescription: { type: 'offer', sdp: 'mock-sdp' },
  remoteDescription: null,
  iceGatheringState: 'new',
  iceConnectionState: 'new',
  connectionState: 'new',
  createDataChannel: vi.fn(() => mockDataChannel),
  createOffer: vi.fn(() => Promise.resolve({ type: 'offer', sdp: 'mock-offer-sdp' })),
  createAnswer: vi.fn(() => Promise.resolve({ type: 'answer', sdp: 'mock-answer-sdp' })),
  setLocalDescription: vi.fn(() => Promise.resolve()),
  setRemoteDescription: vi.fn(() => Promise.resolve()),
  addIceCandidate: vi.fn(() => Promise.resolve()),
  close: vi.fn(),
  onicecandidate: null,
  onicegatheringstatechange: null,
  oniceconnectionstatechange: null,
  onconnectionstatechange: null,
  ondatachannel: null,
  addEventListener: vi.fn(),
  removeEventListener: vi.fn()
};

// Mock RTCPeerConnection globally
global.RTCPeerConnection = vi.fn(() => mockPeerConnection);

// Mock crypto for nacl
vi.mock('../../../src/lib/crypto/nacl.js', () => ({
  encrypt: vi.fn((data, key) => Promise.resolve(data)),
  decrypt: vi.fn((data, key) => Promise.resolve(data)),
  NonceCounter: class {
    constructor() { this.value = 0; }
    next() { return new Uint8Array(24); }
  }
}));

// Now import the module under test
import {
  TransitHandler,
  TransitState,
  createTransitHints,
  parseTransitHints,
  negotiateTransit
} from '../../../src/lib/protocol/transit.js';

describe('TransitHandler', () => {
  let transit;

  beforeEach(() => {
    vi.clearAllMocks();
    mockPeerConnection.iceGatheringState = 'complete';
    mockPeerConnection.iceConnectionState = 'new';
    mockDataChannel.readyState = 'connecting';

    transit = new TransitHandler({
      transitKey: new Uint8Array(32)
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('constructor', () => {
    it('should initialize with DISCONNECTED state', () => {
      expect(transit.state).toBe(TransitState.DISCONNECTED);
    });

    it('should store transit key', () => {
      expect(transit.transitKey).toBeInstanceOf(Uint8Array);
      expect(transit.transitKey.length).toBe(32);
    });

    it('should use default ICE servers', () => {
      expect(transit.iceServers).toBeDefined();
      expect(transit.iceServers.length).toBeGreaterThan(0);
    });

    it('should accept custom ICE servers', () => {
      const customServers = [{ urls: 'stun:custom.server.com:3478' }];
      const customTransit = new TransitHandler({
        iceServers: customServers
      });
      expect(customTransit.iceServers).toBe(customServers);
    });

    it('should initialize empty candidates array', () => {
      expect(transit.localCandidates).toEqual([]);
    });

    it('should initialize null handlers', () => {
      expect(transit.onOpen).toBeNull();
      expect(transit.onClose).toBeNull();
      expect(transit.onError).toBeNull();
      expect(transit.onMessage).toBeNull();
    });
  });

  describe('createOffer', () => {
    it('should set state to CONNECTING', async () => {
      await transit.createOffer();
      expect(transit.state).toBe(TransitState.CONNECTING);
    });

    it('should create RTCPeerConnection', async () => {
      await transit.createOffer();
      expect(global.RTCPeerConnection).toHaveBeenCalled();
    });

    it('should create data channel', async () => {
      await transit.createOffer();
      expect(mockPeerConnection.createDataChannel).toHaveBeenCalledWith('transit', { ordered: true });
    });

    it('should create and set local description', async () => {
      await transit.createOffer();
      expect(mockPeerConnection.createOffer).toHaveBeenCalled();
      expect(mockPeerConnection.setLocalDescription).toHaveBeenCalled();
    });

    it('should return offer and candidates', async () => {
      const result = await transit.createOffer();
      expect(result).toHaveProperty('offer');
      expect(result).toHaveProperty('candidates');
    });
  });

  describe('acceptOffer', () => {
    it('should set state to CONNECTING', async () => {
      const offer = { type: 'offer', sdp: 'mock-sdp' };
      await transit.acceptOffer(offer, []);
      expect(transit.state).toBe(TransitState.CONNECTING);
    });

    it('should set remote description', async () => {
      const offer = { type: 'offer', sdp: 'mock-sdp' };
      await transit.acceptOffer(offer, []);
      expect(mockPeerConnection.setRemoteDescription).toHaveBeenCalledWith(offer);
    });

    it('should add ICE candidates', async () => {
      const offer = { type: 'offer', sdp: 'mock-sdp' };
      const candidates = [{ candidate: 'mock-candidate' }];
      await transit.acceptOffer(offer, candidates);
      expect(mockPeerConnection.addIceCandidate).toHaveBeenCalledWith(candidates[0]);
    });

    it('should create and return answer', async () => {
      const offer = { type: 'offer', sdp: 'mock-sdp' };
      const result = await transit.acceptOffer(offer, []);
      expect(mockPeerConnection.createAnswer).toHaveBeenCalled();
      expect(result).toHaveProperty('answer');
      expect(result).toHaveProperty('candidates');
    });
  });

  describe('completeConnection', () => {
    beforeEach(async () => {
      await transit.createOffer();
    });

    it('should set remote description', async () => {
      const answer = { type: 'answer', sdp: 'mock-answer-sdp' };
      await transit.completeConnection(answer, []);
      expect(mockPeerConnection.setRemoteDescription).toHaveBeenCalledWith(answer);
    });

    it('should add ICE candidates', async () => {
      const answer = { type: 'answer', sdp: 'mock-answer-sdp' };
      const candidates = [{ candidate: 'mock-candidate' }];
      await transit.completeConnection(answer, candidates);
      expect(mockPeerConnection.addIceCandidate).toHaveBeenCalled();
    });

    it('should add pending candidates', async () => {
      transit.pendingRemoteCandidates = [{ candidate: 'pending' }];
      const answer = { type: 'answer', sdp: 'mock-answer-sdp' };
      await transit.completeConnection(answer, []);
      expect(mockPeerConnection.addIceCandidate).toHaveBeenCalled();
      expect(transit.pendingRemoteCandidates).toEqual([]);
    });
  });

  describe('addIceCandidate', () => {
    it('should add candidate when remote description exists', async () => {
      await transit.createOffer();
      mockPeerConnection.remoteDescription = { type: 'answer', sdp: 'mock' };
      await transit.addIceCandidate({ candidate: 'new-candidate' });
      expect(mockPeerConnection.addIceCandidate).toHaveBeenCalled();
    });

    it('should queue candidate when no remote description', async () => {
      await transit.createOffer();
      mockPeerConnection.remoteDescription = null;
      await transit.addIceCandidate({ candidate: 'pending' });
      expect(transit.pendingRemoteCandidates).toContainEqual({ candidate: 'pending' });
    });
  });

  describe('send', () => {
    beforeEach(async () => {
      await transit.createOffer();
      transit.dataChannel = mockDataChannel;
      mockDataChannel.readyState = 'open';
    });

    it('should throw if channel not open', async () => {
      mockDataChannel.readyState = 'connecting';
      await expect(transit.send('test')).rejects.toThrow('Data channel not open');
    });

    it('should send data through data channel', async () => {
      await transit.send(new Uint8Array([1, 2, 3]));
      expect(mockDataChannel.send).toHaveBeenCalled();
    });

    it('should convert string to Uint8Array', async () => {
      await transit.send('hello');
      expect(mockDataChannel.send).toHaveBeenCalled();
    });
  });

  describe('encryptMessage', () => {
    it('should pass through if no transit key', async () => {
      const noKeyTransit = new TransitHandler({});
      const data = new Uint8Array([1, 2, 3]);
      const result = await noKeyTransit.encryptMessage(data);
      expect(result).toBe(data);
    });

    it('should encrypt when transit key exists', async () => {
      const data = new Uint8Array([1, 2, 3]);
      const result = await transit.encryptMessage(data);
      expect(result).toBeDefined();
    });
  });

  describe('decryptMessage', () => {
    it('should pass through if no transit key', async () => {
      const noKeyTransit = new TransitHandler({});
      const data = new Uint8Array([1, 2, 3]);
      const result = await noKeyTransit.decryptMessage(data);
      expect(result).toBe(data);
    });

    it('should decrypt when transit key exists', async () => {
      const data = new Uint8Array([1, 2, 3]);
      const result = await transit.decryptMessage(data);
      expect(result).toBeDefined();
    });
  });

  describe('close', () => {
    beforeEach(async () => {
      await transit.createOffer();
      transit.dataChannel = mockDataChannel;
    });

    it('should close data channel', () => {
      transit.close();
      expect(mockDataChannel.close).toHaveBeenCalled();
    });

    it('should close peer connection', () => {
      transit.close();
      expect(mockPeerConnection.close).toHaveBeenCalled();
    });

    it('should set state to CLOSED', () => {
      transit.close();
      expect(transit.state).toBe(TransitState.CLOSED);
    });

    it('should clear references', () => {
      transit.close();
      expect(transit.dataChannel).toBeNull();
      expect(transit.peerConnection).toBeNull();
    });
  });

  describe('isConnected', () => {
    it('should return false when disconnected', () => {
      expect(transit.isConnected).toBe(false);
    });

    it('should return false when state is connected but no data channel', async () => {
      await transit.createOffer();
      transit.state = TransitState.CONNECTED;
      transit.dataChannel = null;
      expect(transit.isConnected).toBeFalsy();
    });

    it('should return false when data channel not open', async () => {
      await transit.createOffer();
      transit.state = TransitState.CONNECTED;
      transit.dataChannel = mockDataChannel;
      mockDataChannel.readyState = 'connecting';
      expect(transit.isConnected).toBe(false);
    });

    it('should return true when connected with open data channel', async () => {
      await transit.createOffer();
      transit.state = TransitState.CONNECTED;
      transit.dataChannel = mockDataChannel;
      mockDataChannel.readyState = 'open';
      expect(transit.isConnected).toBe(true);
    });
  });
});

describe('TransitState', () => {
  it('should have all states defined', () => {
    expect(TransitState.DISCONNECTED).toBe('disconnected');
    expect(TransitState.CONNECTING).toBe('connecting');
    expect(TransitState.CONNECTED).toBe('connected');
    expect(TransitState.FAILED).toBe('failed');
    expect(TransitState.CLOSED).toBe('closed');
  });
});

describe('createTransitHints', () => {
  it('should create hints from description and candidates', () => {
    const description = { type: 'offer', sdp: 'mock-sdp' };
    const candidates = [
      { candidate: 'candidate1', sdpMid: '0', sdpMLineIndex: 0 }
    ];

    const hints = createTransitHints(description, candidates);

    expect(hints.type).toBe('webrtc');
    expect(hints.sdp).toBe('mock-sdp');
    expect(hints.sdpType).toBe('offer');
    expect(hints.candidates).toHaveLength(1);
    expect(hints.candidates[0].candidate).toBe('candidate1');
  });

  it('should handle empty candidates', () => {
    const description = { type: 'answer', sdp: 'mock-sdp' };
    const hints = createTransitHints(description, []);

    expect(hints.candidates).toEqual([]);
  });
});

describe('parseTransitHints', () => {
  it('should parse valid hints', () => {
    const hints = {
      type: 'webrtc',
      sdp: 'mock-sdp',
      sdpType: 'offer',
      candidates: [{ candidate: 'c1' }]
    };

    const result = parseTransitHints(hints);

    expect(result.description.type).toBe('offer');
    expect(result.description.sdp).toBe('mock-sdp');
    expect(result.candidates).toHaveLength(1);
  });

  it('should return null for non-webrtc hints', () => {
    const hints = { type: 'tcp' };
    expect(parseTransitHints(hints)).toBeNull();
  });

  it('should return null for null input', () => {
    expect(parseTransitHints(null)).toBeNull();
  });

  it('should return null for undefined input', () => {
    expect(parseTransitHints(undefined)).toBeNull();
  });

  it('should handle missing candidates', () => {
    const hints = {
      type: 'webrtc',
      sdp: 'mock-sdp',
      sdpType: 'answer'
    };

    const result = parseTransitHints(hints);
    expect(result.candidates).toEqual([]);
  });
});

describe('negotiateTransit', () => {
  let mockMailbox;
  let transit;

  beforeEach(() => {
    mockMailbox = {
      addMessage: vi.fn(() => Promise.resolve()),
      waitForPhase: vi.fn(() => Promise.resolve(JSON.stringify({
        type: 'webrtc',
        sdp: 'mock-sdp',
        sdpType: 'answer',
        candidates: []
      })))
    };

    transit = new TransitHandler({ transitKey: new Uint8Array(32) });
  });

  it('should create offer when initiator', async () => {
    await negotiateTransit(mockMailbox, true, transit);

    expect(mockPeerConnection.createOffer).toHaveBeenCalled();
    expect(mockMailbox.addMessage).toHaveBeenCalledWith('transit', expect.any(String));
    expect(mockMailbox.waitForPhase).toHaveBeenCalledWith('transit');
  });

  it('should accept offer when not initiator', async () => {
    mockMailbox.waitForPhase = vi.fn(() => Promise.resolve(JSON.stringify({
      type: 'webrtc',
      sdp: 'mock-offer-sdp',
      sdpType: 'offer',
      candidates: []
    })));

    await negotiateTransit(mockMailbox, false, transit);

    expect(mockMailbox.waitForPhase).toHaveBeenCalledWith('transit');
    expect(mockPeerConnection.setRemoteDescription).toHaveBeenCalled();
    expect(mockPeerConnection.createAnswer).toHaveBeenCalled();
    expect(mockMailbox.addMessage).toHaveBeenCalledWith('transit', expect.any(String));
  });

  it('should throw on invalid hints from peer', async () => {
    mockMailbox.waitForPhase = vi.fn(() => Promise.resolve(JSON.stringify({
      type: 'tcp'  // Invalid - not webrtc
    })));

    await expect(negotiateTransit(mockMailbox, true, transit)).rejects.toThrow('Invalid transit hints from peer');
  });
});

describe('Event Handlers', () => {
  let transit;

  beforeEach(async () => {
    transit = new TransitHandler({ transitKey: new Uint8Array(32) });
    await transit.createOffer();
    transit.dataChannel = mockDataChannel;
  });

  describe('data channel onopen', () => {
    it('should set state to CONNECTED', () => {
      transit.setupDataChannelHandlers(mockDataChannel);
      mockDataChannel.onopen();
      expect(transit.state).toBe(TransitState.CONNECTED);
    });

    it('should call onOpen handler', () => {
      const handler = vi.fn();
      transit.onOpen = handler;
      transit.setupDataChannelHandlers(mockDataChannel);
      mockDataChannel.onopen();
      expect(handler).toHaveBeenCalled();
    });
  });

  describe('data channel onclose', () => {
    it('should set state to CLOSED', () => {
      transit.setupDataChannelHandlers(mockDataChannel);
      mockDataChannel.onclose();
      expect(transit.state).toBe(TransitState.CLOSED);
    });

    it('should call onClose handler', () => {
      const handler = vi.fn();
      transit.onClose = handler;
      transit.setupDataChannelHandlers(mockDataChannel);
      mockDataChannel.onclose();
      expect(handler).toHaveBeenCalled();
    });
  });

  describe('data channel onerror', () => {
    it('should set state to FAILED', () => {
      transit.setupDataChannelHandlers(mockDataChannel);
      mockDataChannel.onerror({ error: new Error('test error') });
      expect(transit.state).toBe(TransitState.FAILED);
    });

    it('should call onError handler', () => {
      const handler = vi.fn();
      transit.onError = handler;
      transit.setupDataChannelHandlers(mockDataChannel);
      mockDataChannel.onerror({ error: new Error('test error') });
      expect(handler).toHaveBeenCalled();
    });
  });
});
