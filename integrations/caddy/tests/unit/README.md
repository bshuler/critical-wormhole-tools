# Unit Tests - Error Handling

This directory contains comprehensive unit tests for error handling across the Caddy Wormhole integration.

## Test File: `error_handling_test.go`

### Overview

The error handling test suite contains 20+ test cases covering various error scenarios in the wormhole daemon client API. All tests use mock HTTP servers to simulate error conditions without requiring actual wormhole connections.

### Test Categories

#### 1. Connection Errors
- **TestDaemonClient_ConnectionTimeout**: Verifies timeout error when server doesn't respond
- **TestDaemonClient_ConnectionRefused**: Tests connection refused error handling
- **TestDaemonClient_ServerDisconnect**: Tests handling of abrupt connection termination

#### 2. HTTP Protocol Errors
- **TestDaemonClient_HTTPTimeout**: Validates HTTP request timeout handling
- **TestDaemonClient_StatusNon200**: Tests various HTTP error status codes (400, 401, 403, 500, 503)

#### 3. Wormhole Protocol Errors
- **TestDaemonClient_Resolve_InvalidAddress**: Tests invalid address resolution
- **TestDaemonClient_Connect_DilationFailure**: Validates dilation handshake failure handling
- **TestParseWormholeAddress_Empty**: Tests empty address validation

#### 4. Listener Errors
- **TestDaemonClient_Listen_PortInUse**: Tests "address already in use" error
- **TestDaemonClient_Accept_ListenerNotFound**: Tests missing listener error
- **TestDaemonClient_Accept_ListenerClosed**: Tests closed listener error
- **TestDaemonClient_CloseListener_NotFound**: Tests idempotent listener close

#### 5. Connection Management Errors
- **TestDaemonClient_Send_ConnectionNotFound**: Tests sending to non-existent connection
- **TestDaemonClient_Send_ConnectionClosed**: Tests sending to closed connection
- **TestDaemonClient_Send_InvalidJSON**: Tests malformed JSON response handling
- **TestDaemonClient_CloseConnection_NotFound**: Tests idempotent connection close

#### 6. Data Transfer Errors
- **TestDaemonClient_Recv_EOF**: Tests proper EOF handling on connection close
- **TestDaemonClient_Recv_Timeout**: Tests receive timeout behavior
- **TestDaemonClient_Recv_InvalidJSON**: Tests successful data receive flow

#### 7. Context Management
- **TestDaemonClient_ContextCancellation**: Tests context cancellation handling

### Running the Tests

From the caddy integration root directory:

```bash
# Run all tests
go test ./tests/unit/...

# Run with verbose output
go test -v ./tests/unit/...

# Run specific test
go test -v ./tests/unit/ -run TestDaemonClient_ConnectionTimeout

# Run with coverage
go test -cover ./tests/unit/...
```

Using make:

```bash
# Run all tests (includes unit tests)
make test

# Run with coverage report
make test-coverage
```

### Test Design Principles

1. **Isolation**: Each test uses `httptest.NewServer` to create isolated mock servers
2. **No External Dependencies**: Tests don't require actual wormhole daemon or network connectivity
3. **Error Verification**: Tests check both error presence and error message content
4. **Cleanup**: All tests use `defer` to ensure proper resource cleanup
5. **Context Awareness**: Tests properly handle context cancellation and timeouts

### Coverage

The error handling test suite covers:
- ✅ Connection timeouts and failures
- ✅ HTTP protocol errors (all common status codes)
- ✅ Wormhole-specific errors (dilation, resolution, etc.)
- ✅ Listener lifecycle errors
- ✅ Connection lifecycle errors
- ✅ Data transfer errors (EOF, timeouts)
- ✅ Context cancellation
- ✅ JSON parsing errors
- ✅ Address validation

### Error Types Tested

| Error Type | Example Test |
|------------|--------------|
| `net.Error` (timeout) | `TestDaemonClient_ConnectionTimeout` |
| `io.EOF` | `TestDaemonClient_Recv_EOF` |
| `context.Canceled` | `TestDaemonClient_ContextCancellation` |
| HTTP Status Errors | `TestDaemonClient_StatusNon200` |
| Wormhole Protocol Errors | `TestDaemonClient_Connect_DilationFailure` |
| Validation Errors | `TestParseWormholeAddress_Empty` |

### Adding New Tests

When adding new error handling tests:

1. Use descriptive test names: `TestComponent_Scenario`
2. Create isolated mock servers with `httptest.NewServer`
3. Verify error is non-nil
4. Check error type/message content
5. Use `defer` for cleanup
6. Add test to this README

### Notes

- All tests are in the `wormhole` package to access package-private functions
- Tests use standard library `testing` package
- Mock servers automatically clean up via `defer server.Close()`
- Tests are designed to run quickly (< 1s each) for rapid development
