/**
 * Unit tests for Dilation Manager
 *
 * Tests the dilation protocol implementation for browser extension.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock crypto functions BEFORE importing dilation
vi.mock('../../src/lib/crypto/nacl.js', () => ({
  encrypt: vi.fn((data, key) => Promise.resolve(data)),  // Pass through for testing
  decrypt: vi.fn((data, key) => Promise.resolve(data)),  // Pass through for testing
  NonceCounter: class {
    constructor() { this.value = 0; }
    next() { return new Uint8Array(24); }
  }
}));

vi.mock('../../src/lib/crypto/hkdf.js', () => ({
  derivePhaseKey: vi.fn(() => Promise.resolve(new Uint8Array(32)))
}));

// Now import the module under test
import {
  DilationManager,
  DilationState,
  DilationMessageType,
  RecordType,
  Subchannel,
  createEndpoints
} from '../../src/lib/protocol/dilation.js';

// Mock mailbox
function createMockMailbox() {
  return {
    side: 'side-abc123',
    onMessage: vi.fn(() => () => {}),  // Returns unsubscribe function
    addMessage: vi.fn(() => Promise.resolve())
  };
}

describe('DilationManager', () => {
  let manager;
  let mockMailbox;

  beforeEach(() => {
    mockMailbox = createMockMailbox();

    manager = new DilationManager({
      mailbox: mockMailbox,
      sharedKey: new Uint8Array(32),
      mailboxSide: 'side-abc123',
      peerSide: 'side-def456'
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('constructor', () => {
    it('should initialize with IDLE state', () => {
      expect(manager.state).toBe(DilationState.IDLE);
    });

    it('should store mailbox reference', () => {
      expect(manager.mailbox).toBe(mockMailbox);
    });

    it('should initialize empty subchannels map', () => {
      expect(manager.subchannels.size).toBe(0);
    });

    it('should set default ICE servers', () => {
      expect(manager.iceServers).toBeDefined();
      expect(manager.iceServers.length).toBeGreaterThan(0);
    });
  });

  describe('setState', () => {
    it('should update state', () => {
      manager.setState(DilationState.WAITING);
      expect(manager.state).toBe(DilationState.WAITING);
    });

    it('should call onStateChange callback', () => {
      const callback = vi.fn();
      manager.onStateChange = callback;

      manager.setState(DilationState.WAITING);

      expect(callback).toHaveBeenCalledWith(DilationState.WAITING, DilationState.IDLE);
    });

    it('should not call callback if state unchanged', () => {
      const callback = vi.fn();
      manager.onStateChange = callback;

      manager.setState(DilationState.IDLE);

      expect(callback).not.toHaveBeenCalled();
    });
  });

  describe('isConnected', () => {
    it('should return false when not connected', () => {
      expect(manager.isConnected).toBe(false);
    });

    it('should return false when connected but no control channel', () => {
      manager.state = DilationState.CONNECTED;
      expect(manager.isConnected).toBeFalsy();
    });

    it('should return true when connected with open control channel', () => {
      manager.state = DilationState.CONNECTED;
      manager.controlChannel = { readyState: 'open' };
      expect(manager.isConnected).toBe(true);
    });
  });

  describe('close', () => {
    it('should close all subchannels', async () => {
      const mockSubchannel = { close: vi.fn() };
      manager.subchannels.set(1, mockSubchannel);

      await manager.close();

      expect(mockSubchannel.close).toHaveBeenCalled();
      expect(manager.subchannels.size).toBe(0);
    });

    it('should set state to STOPPED', async () => {
      await manager.close();
      expect(manager.state).toBe(DilationState.STOPPED);
    });

    it('should close WebRTC components', async () => {
      manager.controlChannel = { close: vi.fn() };
      manager.peerConnection = { close: vi.fn() };

      await manager.close();

      expect(manager.controlChannel).toBeNull();
      expect(manager.peerConnection).toBeNull();
    });
  });

  describe('listen', () => {
    it('should register protocol listener', () => {
      const callback = vi.fn();
      manager.listen('wh-test', callback);

      expect(manager.subchannelListeners.get('wh-test')).toBe(callback);
    });
  });

  describe('unlisten', () => {
    it('should remove protocol listener', () => {
      const callback = vi.fn();
      manager.listen('wh-test', callback);
      manager.unlisten('wh-test');

      expect(manager.subchannelListeners.has('wh-test')).toBe(false);
    });
  });
});

describe('Subchannel', () => {
  let subchannel;
  let mockManager;

  beforeEach(() => {
    mockManager = {
      _sendRecord: vi.fn(() => Promise.resolve()),
      subchannels: new Map()
    };

    subchannel = new Subchannel(mockManager, 1, 'wh-test', true);
    mockManager.subchannels.set(1, subchannel);
  });

  describe('constructor', () => {
    it('should initialize with correct properties', () => {
      expect(subchannel.id).toBe(1);
      expect(subchannel.protocol).toBe('wh-test');
      expect(subchannel.isInitiator).toBe(true);
      expect(subchannel.isOpen).toBe(true);
    });
  });

  describe('send', () => {
    it('should call manager._sendRecord with DATA type', async () => {
      const data = new Uint8Array([1, 2, 3]);
      await subchannel.send(data);

      expect(mockManager._sendRecord).toHaveBeenCalledWith(RecordType.DATA, 1, data);
    });

    it('should convert string to Uint8Array', async () => {
      await subchannel.send('hello');

      expect(mockManager._sendRecord).toHaveBeenCalled();
      const [type, id, data] = mockManager._sendRecord.mock.calls[0];
      expect(type).toBe(RecordType.DATA);
      expect(new TextDecoder().decode(data)).toBe('hello');
    });

    it('should throw if subchannel is closed', async () => {
      subchannel.isOpen = false;
      await expect(subchannel.send('test')).rejects.toThrow('Subchannel closed');
    });
  });

  describe('_receiveData', () => {
    it('should call onData callback', () => {
      const callback = vi.fn();
      subchannel.onData = callback;

      const data = new Uint8Array([1, 2, 3]);
      subchannel._receiveData(data);

      expect(callback).toHaveBeenCalledWith(data);
    });

    it('should buffer data if no callback', () => {
      const data = new Uint8Array([1, 2, 3]);
      subchannel._receiveData(data);

      expect(subchannel.receiveBuffer).toContain(data);
    });

    it('should increment recvSeqnum', () => {
      subchannel._receiveData(new Uint8Array([1]));
      expect(subchannel.recvSeqnum).toBe(1);
    });
  });

  describe('close', () => {
    it('should send CLOSE record', async () => {
      await subchannel.close();

      expect(mockManager._sendRecord).toHaveBeenCalledWith(
        RecordType.CLOSE,
        1,
        expect.any(Uint8Array)
      );
    });

    it('should set isOpen to false', async () => {
      await subchannel.close();
      expect(subchannel.isOpen).toBe(false);
    });

    it('should remove from manager.subchannels', async () => {
      await subchannel.close();
      expect(mockManager.subchannels.has(1)).toBe(false);
    });

    it('should not send if already closed', async () => {
      subchannel.isOpen = false;
      await subchannel.close();

      expect(mockManager._sendRecord).not.toHaveBeenCalled();
    });
  });

  describe('read', () => {
    it('should return buffered data', () => {
      const data = new Uint8Array([1, 2, 3]);
      subchannel.receiveBuffer.push(data);

      expect(subchannel.read()).toBe(data);
      expect(subchannel.receiveBuffer.length).toBe(0);
    });

    it('should return null if no data', () => {
      expect(subchannel.read()).toBeNull();
    });
  });

  describe('hasData', () => {
    it('should return true if buffer has data', () => {
      subchannel.receiveBuffer.push(new Uint8Array([1]));
      expect(subchannel.hasData).toBe(true);
    });

    it('should return false if buffer empty', () => {
      expect(subchannel.hasData).toBe(false);
    });
  });
});

describe('createEndpoints', () => {
  let mockManager;

  beforeEach(() => {
    mockManager = {
      openSubchannel: vi.fn(() => Promise.resolve({})),
      listen: vi.fn()
    };
  });

  it('should return connect and listen functions', () => {
    const endpoints = createEndpoints(mockManager);

    expect(endpoints.connect).toBeDefined();
    expect(endpoints.listen).toBeDefined();
  });

  describe('SubchannelConnector', () => {
    it('should call manager.openSubchannel on connect', async () => {
      const endpoints = createEndpoints(mockManager);
      const connector = endpoints.connect('wh-test');

      await connector.connect();

      expect(mockManager.openSubchannel).toHaveBeenCalledWith('wh-test');
    });
  });

  describe('SubchannelListener', () => {
    it('should call manager.listen on listen', async () => {
      const endpoints = createEndpoints(mockManager);
      const listener = endpoints.listen('wh-test');

      await listener.listen();

      expect(mockManager.listen).toHaveBeenCalledWith('wh-test', expect.any(Function));
    });
  });
});

describe('DilationMessageType', () => {
  it('should have correct message types', () => {
    expect(DilationMessageType.PLEASE).toBe('please');
    expect(DilationMessageType.HINTS).toBe('connection-hints');
    expect(DilationMessageType.RECONNECT).toBe('reconnect');
    expect(DilationMessageType.RECONNECTING).toBe('reconnecting');
  });
});

describe('RecordType', () => {
  it('should have correct record types', () => {
    expect(RecordType.OPEN).toBe(0x01);
    expect(RecordType.DATA).toBe(0x02);
    expect(RecordType.CLOSE).toBe(0x03);
    expect(RecordType.ACK).toBe(0x04);
  });
});

describe('DilationState', () => {
  it('should have all states defined', () => {
    expect(DilationState.IDLE).toBe('idle');
    expect(DilationState.WAITING).toBe('waiting');
    expect(DilationState.WANTING).toBe('wanting');
    expect(DilationState.CONNECTING).toBe('connecting');
    expect(DilationState.CONNECTED).toBe('connected');
    expect(DilationState.RECONNECTING).toBe('reconnecting');
    expect(DilationState.FAILED).toBe('failed');
    expect(DilationState.STOPPED).toBe('stopped');
  });
});

// Additional tests for dilation protocol functionality

describe('DilationManager Extended', () => {
  let manager;
  let mockMailbox;

  beforeEach(() => {
    mockMailbox = createMockMailbox();
    manager = new DilationManager({
      mailbox: mockMailbox,
      sharedKey: new Uint8Array(32),
      mailboxSide: 'side-abc123',
      peerSide: 'side-def456'
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('dilate', () => {
    it('should throw if not in IDLE state', async () => {
      manager.state = DilationState.WAITING;
      await expect(manager.dilate()).rejects.toThrow('Cannot dilate in state: waiting');
    });

    it('should set state to WAITING', async () => {
      // Mock the internal methods to prevent full execution
      manager._startDilationMessageHandler = vi.fn();
      manager._sendDilationMessage = vi.fn(() => Promise.resolve());
      manager._waitForConnection = vi.fn(() => Promise.resolve());

      await manager.dilate();
      expect(manager.state).toBe(DilationState.WAITING);
    });

    it('should generate dilation side', async () => {
      manager._startDilationMessageHandler = vi.fn();
      manager._sendDilationMessage = vi.fn(() => Promise.resolve());
      manager._waitForConnection = vi.fn(() => Promise.resolve());

      await manager.dilate();
      expect(manager.dilationSide).toBeDefined();
      expect(manager.dilationSide.length).toBe(16); // 8 bytes = 16 hex chars
    });

    it('should send PLEASE message', async () => {
      manager._startDilationMessageHandler = vi.fn();
      manager._sendDilationMessage = vi.fn(() => Promise.resolve());
      manager._waitForConnection = vi.fn(() => Promise.resolve());

      await manager.dilate();

      expect(manager._sendDilationMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          type: DilationMessageType.PLEASE,
          side: expect.any(String),
          'use-version': 1
        })
      );
    });
  });

  describe('_parseRecord', () => {
    it('should return null for data less than 5 bytes', () => {
      const result = manager._parseRecord(new Uint8Array([1, 2, 3, 4]));
      expect(result).toBeNull();
    });

    it('should parse valid record', () => {
      // Build a record: type (1 byte) + id (4 bytes big-endian) + data
      const record = new Uint8Array(10);
      record[0] = RecordType.DATA;  // type
      new DataView(record.buffer).setUint32(1, 42, false);  // id = 42
      record[5] = 0x01;  // data
      record[6] = 0x02;
      record[7] = 0x03;
      record[8] = 0x04;
      record[9] = 0x05;

      const result = manager._parseRecord(record);

      expect(result.type).toBe(RecordType.DATA);
      expect(result.id).toBe(42);
      expect(result.data).toEqual(new Uint8Array([1, 2, 3, 4, 5]));
    });

    it('should parse OPEN record', () => {
      const record = new Uint8Array(12);
      record[0] = RecordType.OPEN;
      new DataView(record.buffer).setUint32(1, 1, false);
      new TextEncoder().encodeInto('wh-http', record.subarray(5));

      const result = manager._parseRecord(record);

      expect(result.type).toBe(RecordType.OPEN);
      expect(result.id).toBe(1);
    });

    it('should parse ACK record with seqnum', () => {
      const record = new Uint8Array(9);
      record[0] = RecordType.ACK;
      new DataView(record.buffer).setUint32(1, 1, false);  // id
      new DataView(record.buffer).setUint32(5, 123, false);  // seqnum

      const result = manager._parseRecord(record);

      expect(result.type).toBe(RecordType.ACK);
      expect(result.seqnum).toBe(123);
    });
  });

  describe('openSubchannel', () => {
    beforeEach(() => {
      manager.state = DilationState.CONNECTED;
      manager.controlChannel = { readyState: 'open', send: vi.fn() };
      manager._sendRecord = vi.fn(() => Promise.resolve());
    });

    it('should throw if not connected', async () => {
      manager.state = DilationState.IDLE;
      await expect(manager.openSubchannel('wh-test')).rejects.toThrow('Dilation not connected');
    });

    it('should create subchannel with incrementing ID', async () => {
      const sc1 = await manager.openSubchannel('wh-test');
      const sc2 = await manager.openSubchannel('wh-test');

      expect(sc1.id).toBe(1);
      expect(sc2.id).toBe(2);
    });

    it('should send OPEN record', async () => {
      await manager.openSubchannel('wh-http');

      expect(manager._sendRecord).toHaveBeenCalledWith(
        RecordType.OPEN,
        1,
        expect.any(Uint8Array)
      );
    });

    it('should add subchannel to map', async () => {
      const sc = await manager.openSubchannel('wh-test');
      expect(manager.subchannels.get(sc.id)).toBe(sc);
    });

    it('should create initiator subchannel', async () => {
      const sc = await manager.openSubchannel('wh-test');
      expect(sc.isInitiator).toBe(true);
    });
  });

  describe('_handleSubchannelOpen', () => {
    it('should send CLOSE if no listener for protocol', async () => {
      manager._sendRecord = vi.fn(() => Promise.resolve());

      await manager._handleSubchannelOpen({
        id: 1,
        data: new TextEncoder().encode('unknown-protocol')
      });

      expect(manager._sendRecord).toHaveBeenCalledWith(
        RecordType.CLOSE,
        1,
        expect.any(Uint8Array)
      );
    });

    it('should create subchannel and notify listener', async () => {
      const listener = vi.fn();
      manager.listen('wh-test', listener);
      manager._sendRecord = vi.fn(() => Promise.resolve());

      await manager._handleSubchannelOpen({
        id: 5,
        data: new TextEncoder().encode('wh-test')
      });

      expect(listener).toHaveBeenCalled();
      expect(manager.subchannels.has(5)).toBe(true);
    });

    it('should call onSubchannelOpen callback', async () => {
      const callback = vi.fn();
      manager.onSubchannelOpen = callback;
      manager.listen('wh-test', vi.fn());
      manager._sendRecord = vi.fn(() => Promise.resolve());

      await manager._handleSubchannelOpen({
        id: 1,
        data: new TextEncoder().encode('wh-test')
      });

      expect(callback).toHaveBeenCalled();
    });
  });

  describe('_handlePlease', () => {
    beforeEach(() => {
      manager.dilationSide = 'zzzzzzzz';  // High value - will be leader
      manager._startWebRTC = vi.fn(() => Promise.resolve());
    });

    it('should store peer dilation side', async () => {
      await manager._handlePlease({ side: 'aaaaaaaa' });
      expect(manager.peerDilationSide).toBe('aaaaaaaa');
    });

    it('should determine leader (higher side)', async () => {
      await manager._handlePlease({ side: 'aaaaaaaa' });
      expect(manager.isLeader).toBe(true);
    });

    it('should determine follower (lower side)', async () => {
      manager.dilationSide = 'aaaaaaaa';  // Low value
      await manager._handlePlease({ side: 'zzzzzzzz' });
      expect(manager.isLeader).toBe(false);
    });

    it('should set state to WANTING', async () => {
      await manager._handlePlease({ side: 'aaaaaaaa' });
      expect(manager.state).toBe(DilationState.WANTING);
    });

    it('should start WebRTC', async () => {
      await manager._handlePlease({ side: 'aaaaaaaa' });
      expect(manager._startWebRTC).toHaveBeenCalled();
    });
  });

  describe('_sendRecord', () => {
    it('should throw if control channel not open', async () => {
      manager.controlChannel = null;
      await expect(manager._sendRecord(RecordType.DATA, 1, new Uint8Array(0)))
        .rejects.toThrow('Control channel not open');
    });

    it('should throw if control channel ready state is not open', async () => {
      manager.controlChannel = { readyState: 'connecting' };
      await expect(manager._sendRecord(RecordType.DATA, 1, new Uint8Array(0)))
        .rejects.toThrow('Control channel not open');
    });

    it('should build and send record when channel is open', async () => {
      const sendFn = vi.fn();
      manager.controlChannel = { readyState: 'open', send: sendFn };
      manager.dilationKey = new Uint8Array(32);

      await manager._sendRecord(RecordType.DATA, 42, new Uint8Array([1, 2, 3]));

      expect(sendFn).toHaveBeenCalled();
    });
  });
});

describe('Subchannel Extended', () => {
  let subchannel;
  let mockManager;

  beforeEach(() => {
    mockManager = {
      _sendRecord: vi.fn(() => Promise.resolve()),
      subchannels: new Map()
    };
    subchannel = new Subchannel(mockManager, 1, 'wh-test', false);
    mockManager.subchannels.set(1, subchannel);
  });

  describe('_handleClose', () => {
    it('should set isOpen to false', () => {
      subchannel._handleClose(new Uint8Array([0]));
      expect(subchannel.isOpen).toBe(false);
    });

    it('should remove from manager subchannels', () => {
      subchannel._handleClose(new Uint8Array([0]));
      expect(mockManager.subchannels.has(1)).toBe(false);
    });

    it('should call onClose callback', () => {
      const callback = vi.fn();
      subchannel.onClose = callback;
      subchannel._handleClose(new Uint8Array([0]));
      expect(callback).toHaveBeenCalled();
    });
  });

  describe('_handleAck', () => {
    it('should not throw (flow control not implemented)', () => {
      expect(() => subchannel._handleAck(123)).not.toThrow();
    });
  });

  describe('sequence numbers', () => {
    it('should start with zero send seqnum', () => {
      expect(subchannel.sendSeqnum).toBe(0);
    });

    it('should start with zero recv seqnum', () => {
      expect(subchannel.recvSeqnum).toBe(0);
    });

    it('should increment send seqnum after send', async () => {
      await subchannel.send('test');
      expect(subchannel.sendSeqnum).toBe(1);
    });

    it('should increment recv seqnum on receive', () => {
      subchannel._receiveData(new Uint8Array([1]));
      subchannel._receiveData(new Uint8Array([2]));
      expect(subchannel.recvSeqnum).toBe(2);
    });
  });

  describe('non-initiator subchannel', () => {
    it('should have isInitiator false', () => {
      expect(subchannel.isInitiator).toBe(false);
    });
  });
});

describe('SubchannelListener Extended', () => {
  let mockManager;
  let listener;

  beforeEach(() => {
    mockManager = {
      listen: vi.fn(),
      unlisten: vi.fn()
    };

    const endpoints = createEndpoints(mockManager);
    listener = endpoints.listen('wh-test');
  });

  describe('accept', () => {
    it('should return pending connection if available', async () => {
      await listener.listen();

      // Simulate incoming connection via the callback
      const listenCallback = mockManager.listen.mock.calls[0][1];
      const mockSubchannel = { id: 1, protocol: 'wh-test' };
      listenCallback(mockSubchannel);

      const result = await listener.accept();
      expect(result).toBe(mockSubchannel);
    });

    it('should wait for connection if none pending', async () => {
      await listener.listen();

      // Start accept before connection arrives
      const acceptPromise = listener.accept();

      // Simulate incoming connection
      const listenCallback = mockManager.listen.mock.calls[0][1];
      const mockSubchannel = { id: 2, protocol: 'wh-test' };
      listenCallback(mockSubchannel);

      const result = await acceptPromise;
      expect(result).toBe(mockSubchannel);
    });
  });

  describe('close', () => {
    it('should call manager.unlisten', () => {
      listener.close();
      expect(mockManager.unlisten).toHaveBeenCalledWith('wh-test');
    });
  });
});
