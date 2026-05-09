# CivetWeb Test Suite — ALT Linux Packaging

This document describes the unit and integration test suite as configured for
ALT Linux Sisyphus packaging. The test runner is **ctest** backed by the
[libcheck](https://libcheck.github.io/check/) unit-testing framework.

## Build-time requirements

```
BuildRequires: ctest libcheck-devel
BuildRequires: rpm-build-vm iproute2   # IPv6 test via vm-run
BuildRequires: openssl-devel           # TLS tests
BuildRequires: liblua5.3-devel         # Lua scripting tests
BuildRequires: libduktape-devel        # Duktape scripting tests
```

The CGI helper binary `output/cgi_test.cgi` is compiled in `%check` before
running ctest:

```spec
mkdir -p output
gcc -o output/cgi_test.cgi unittest/cgi_test.c
```

## Running the tests

```bash
cd %_cmake__builddir
CTEST_OUTPUT_ON_FAILURE=1 ctest -E "$CTEST_EXCLUDE"
```

Tests that require a network-capable loopback (IPv6) run separately via
`rpm-build-vm`:

```bash
vm-run --kvm=cond --sbin \
    "ip link set lo up; cd $PWD && CTEST_OUTPUT_ON_FAILURE=1 \
     ctest -R test-publicserver-start-stop-http-server-ipv6"
```

## ALT-specific patches affecting tests

| Patch | Effect on tests |
|-------|----------------|
| `0001` | Replaces `ExternalProject_Add(check)` with system `libcheck-devel` |
| `0004` | Adds `WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}` and `LOCAL_TEST` define so SSL cert and resource paths resolve correctly inside hasher chroot |
| `0005` | Adds Lua (port 8090) and Duktape (port 8091) integration tests |
| `0006` | Extends `#if defined(OPENSSL_API_1_1)` guard to `|| defined(OPENSSL_API_3_0)` in TLS client test |
| `0007` | Adds WebSocket Basic (port 8092) and TLS with OpenSSL3 (port 8093s) tests |

## Excluded / special-cased tests

| ctest name | Reason | How handled |
|-----------|--------|------------|
| `test-publicserver-minimal-http-client` | Connects to github.com / google.com — no external DNS in hasher | Excluded via `-E` |
| `test-publicserver-minimal-https-client` | Same | Excluded via `-E` |
| `test-publicserver-start-stop-http-server-ipv6` | Requires IPv6 loopback (`::1`) — not available in hasher without root | Run via `vm-run --kvm=cond` after `ip link set lo up` |

Scripting tests can be skipped with `--without scripting_tests` (RPM build flag):

```
rpmbuild --without scripting_tests ...
```

This excludes `test-publicserver-lua-script` and `test-publicserver-duktape-script`.

---

## Test catalogue

### Suite: Private — internal function unit tests

Source: `unittest/private.c`

| ctest name | Function | What is tested |
|-----------|----------|----------------|
| `test-private-http-message` | `test_parse_http_message` | HTTP request/response parser: method, URI, version, headers, body offsets; malformed input rejection |
| `test-private-http-keep-alive` | `test_should_keep_alive` | `Connection: keep-alive` vs `close` logic for HTTP/1.0 and HTTP/1.1 |
| `test-private-url-parsing-1` | `test_match_prefix` | URI prefix pattern matching (wildcard, exact, length limits) |
| `test-private-url-parsing-2` | `test_match_prefix_strlen` | Same with strlen-based bounds |
| `test-private-url-parsing-3` | `test_match_prefix_fuzz` | Fuzz variants of prefix matching to catch edge cases |
| `test-private-internal-parsing-1` | `test_mg_match` | `mg_match()` pattern matching function |
| `test-private-internal-parsing-2` | `test_remove_dot_segments` | Path normalization: `/../`, `/./`, double-slash removal |
| `test-private-internal-parsing-3` | `test_is_valid_uri` | URI character class validation |
| `test-private-internal-parsing-4` | `test_next_option` | `next_option()` iterator for comma-separated configuration strings |
| `test-private-internal-parsing-5` | `test_skip_quoted` | Quoted-string skipping in header values |
| `test-private-internal-parsing-6` | `test_alloc_vprintf` | Dynamic string allocation via vprintf-style formatting |
| `test-private-internal-parsing-7` | `test_mg_vsnprintf` | `mg_vsnprintf()` truncation and NUL-termination guarantees |
| `test-private-encode-decode` | `test_encode_decode` | URL percent-encoding and decoding round-trips |
| `test-private-mask-data` | `test_mask_data` | WebSocket frame masking / unmasking (XOR with 4-byte key) |
| `test-private-date-parsing` | `test_parse_date_string` | HTTP date string parsing (`Date:`, `If-Modified-Since:`) |
| `test-private-sha1` | `test_sha1` | SHA-1 implementation (used for WebSocket handshake `Sec-WebSocket-Accept`) |
| `test-private-config-options` | `test_config_options` | All `mg_get_valid_options()` entries have default values and expected types |

---

### Suite: PublicFunc — public API utility functions

Source: `unittest/public_func.c`

| ctest name | Function | What is tested |
|-----------|----------|----------------|
| `test-publicfunc-version` | `test_mg_version` | `mg_version()` returns a non-empty semver string |
| `test-publicfunc-options` | `test_mg_get_valid_options` | `mg_get_valid_options()` returns a complete, NULL-terminated option table |
| `test-publicfunc-mime-types` | `test_mg_get_builtin_mime_type` | Built-in MIME type lookup for common extensions (`.html`, `.js`, `.png`, …) |
| `test-publicfunc-strcasecmp` | `test_mg_strncasecmp` | Case-insensitive string comparison |
| `test-publicfunc-url-encoding-decoding` | `test_mg_url_encode` / `test_mg_url_decode` | Percent-encode special characters; decode back; round-trip |
| `test-publicfunc-base64-encoding-decoding` | `test_mg_base64` | Base64 encode/decode; padding; binary data |
| `test-publicfunc-cookies-and-variables` | `test_mg_get_cookie` / `test_mg_get_var` | Cookie header parsing; form variable extraction from query string and body |
| `test-publicfunc-md5` | `test_mg_md5` | MD5 implementation used for HTTP Digest authentication |
| `test-publicfunc-aux-functions` | `test_mg_get_response_code_text` | HTTP status code → reason phrase mapping |

---

### Suite: PublicServer — server integration tests

Source: `unittest/public_server.c`

All tests in this suite start a real `mg_context` and connect to it via
`mg_connect_client()` or the WebSocket client API.

#### Environment and initialization

| ctest name | Function | What is tested |
|-----------|----------|----------------|
| `test-publicserver-check-test-environment` | `test_the_test_environment` | `resources/ssl_cert.pem` is readable in the working directory; sanity-checks `locate_ssl_cert()` path resolution (`LOCAL_TEST` define, patch 0004) |
| `test-publicserver-init-library` | `test_init_library` | `mg_init_library()` / `mg_exit_library()` lifecycle; `mg_check_feature()` returns correct bits for the compiled feature set (SSL, IPv6, WebSocket, Lua, Duktape) |
| `test-publicserver-start-threads` | `test_threading` | `mg_start_thread()` creates a joinable POSIX thread; thread function and data pointer are passed correctly |

#### HTTP server start/stop

| ctest name | Function | What is tested |
|-----------|----------|----------------|
| `test-publicserver-minimal-http-server` | `test_minimal_http_server_callback` | Start server with `begin_request` callback; verify GET returns callback-generated response; stop cleanly |
| `test-publicserver-minimal-https-server` | `test_minimal_https_server_callback` | Same over HTTPS (port 8443s, `ssl_cert.pem`); verifies TLS handshake succeeds with direct OpenSSL linking (`NO_SSL_DL`) |
| `test-publicserver-start-stop-http-server` | `test_mg_start_stop_http_server` | `mg_start()` / `mg_stop()` cycle twice (plain HTTP); verifies `mg_get_server_ports()` returns correct port/protocol/ssl flags |
| `test-publicserver-start-stop-http-server-ipv6` | `test_mg_start_stop_http_server_ipv6` | Same over IPv6 (`[::1]`); requires loopback to be up — **runs via `vm-run --kvm=cond`** with `ip link set lo up` |
| `test-publicserver-start-stop-https-server` | `test_mg_start_stop_https_server` | `mg_start()` with `8080r,8443s`; verifies redirect port and SSL port are reported; makes one HTTPS GET |

#### TLS / SSL

| ctest name | Function | What is tested |
|-----------|----------|----------------|
| `test-publicserver-tls-server-client` | `test_mg_server_and_client_tls` | Server requires a client certificate (`ssl_ca_file`); connection **without** client cert fails or is unusable (guarded for both `OPENSSL_API_1_1` and `OPENSSL_API_3_0` — patch 0006); connection **with** correct client cert succeeds and exchanges data |
| `test-publicserver-tls-with-openssl3` *(patch 0007)* | `test_tls_openssl3` | Verifies at **runtime** that `OpenSSL_version_num() >= 0x30000000L` (i.e., the system OpenSSL is actually 3.x, not just compiled with 3.0 headers); starts HTTPS server on port 8093s; makes an encrypted GET to `/tls3check`; asserts HTTP 200 and correct body — end-to-end proof that the `OPENSSL_API_3_0` code path works |

#### Request handlers and HTTP features

| ctest name | Function | What is tested |
|-----------|----------|----------------|
| `test-publicserver-minimal-http-client` | `test_minimal_client` | **EXCLUDED** — connects to external servers (github.com, google.com); no external DNS in hasher |
| `test-publicserver-minimal-https-client` | `test_minimal_tls_client` | **EXCLUDED** — same reason |
| `test-publicserver-server-requests` | `test_request_handlers` | Comprehensive handler test: 1000+ URI handlers registered/removed, CGI execution (`cgi_test.cgi`), WebSocket echo (ports 8084/8086/8094), HTTP/HTTPS serving, redirect ports, form data, auth, large payloads; also exercises WebSocket multi-client if `USE_WEBSOCKET` |
| `test-publicserver-store-body` | `test_mg_store_body` | POST body storage via `mg_store_body()`; large body > 4 KB; temp file creation and cleanup |
| `test-publicserver-handle-form` | `test_handle_form` | `mg_handle_form_request()`: `application/x-www-form-urlencoded`, `multipart/form-data`, file uploads, field callbacks |
| `test-publicserver-http-authentication` | `test_http_auth` | HTTP Digest authentication; valid credentials, wrong password, missing auth header |
| `test-publicserver-http-keep-alive` | `test_keep_alive` | HTTP/1.1 persistent connections; multiple requests on one TCP socket; `Connection: close` termination |
| `test-publicserver-error-handling` | `test_error_handling` | `http_error` callback receives correct status codes (404, 403, 500); custom error pages override default |
| `test-publicserver-error-logging` | `test_error_log_file` | `error_log_file` config writes messages; `log_message` callback suppresses default logging when returning non-zero |
| `test-publicserver-limit-speed` | `test_throttle` | `throttle` configuration limits transfer rate; timed measurement of actual throughput |
| `test-publicserver-large-file` | `test_large_file` | Static file serving of a file > 2 MB; `Range:` partial content; chunked response; `If-Modified-Since:` 304 |

#### Scripting engines

| ctest name | Condition | Function | What is tested |
|-----------|-----------|----------|----------------|
| `test-publicserver-lua-script` | `USE_LUA` | `test_lua_script` | Server on port 8090, `document_root=resources/`; GET `/test_lua.lua` → HTTP 200, body contains `Hello from Lua!`; verifies `mg.write()` produces a complete HTTP response (patch 0005) |
| `test-publicserver-duktape-script` | `USE_DUKTAPE` | `test_duktape_script` | Server on port 8091; GET `/test_duktape.ssjs` → HTTP 200, body contains `Hello from Duktape!`; verifies `conn.write()` and Duktape 2.x API compatibility (patch 0005) |

#### WebSocket

| ctest name | Condition | Function | What is tested |
|-----------|-----------|----------|----------------|
| `test-publicserver-websocket-basic` *(patch 0007)* | `USE_WEBSOCKET` | `test_websocket_basic` | All four documented `mg_set_websocket_handler()` callbacks: **connect** (returns 0 = accept), **ready** (sends `ws-welcome` via `mg_websocket_write()`), **data** (ping→pong, bye→done, returns 0 to close), **close**; client side: `mg_connect_websocket_client()`, `mg_websocket_client_write()`; `mg_check_feature(MG_FEATURES_WEBSOCKET)` asserted |

---

### Suite: Timer — internal timer subsystem

Source: `unittest/timertest.c`

| ctest name | Function | What is tested |
|-----------|----------|----------------|
| `test-timer-timer-single-shot` | `test_timer_oneshot_by_callback_retval` | One-shot timer fires exactly once; callback returning 0 cancels re-scheduling |
| `test-timer-timer-periodic` | `test_timer_cyclic` | Periodic timer fires N times within expected interval; `mg_set_timer()` precision |
| `test-timer-timer-mixed` | `test_timer_mixed` | Mix of one-shot and periodic timers; cancellation via `mg_cancel_timer()` |

---

### Suite: EXE — standalone executable helpers

Source: `unittest/private_exe.c`

| ctest name | Function | What is tested |
|-----------|----------|----------------|
| `test-exe-helper-funcs` | `test_helper_funcs` | Command-line option parsing in `main.c`; `--help` output; config file loading |

---

## Port assignments

| Port | Protocol | Used by |
|------|----------|---------|
| 8080 | HTTP | `start-stop-https-server` (redirect), `request-handlers` |
| 8084 | HTTP | `request-handlers` (IPv4) |
| 8086 | HTTP | `request-handlers` (IPv6) |
| 8090 | HTTP | `lua-script` (patch 0005) |
| 8091 | HTTP | `duktape-script` (patch 0005) |
| 8092 | HTTP | `websocket-basic` (patch 0007) |
| 8093 | HTTPS | `tls-with-openssl3` (patch 0007) |
| 8094 | HTTPS | `request-handlers` (SSL) |
| 8096 | HTTPS | `request-handlers` (IPv6 SSL) |
| 8194 | HTTP | `request-handlers` (redirect) |
| 8196 | HTTP | `request-handlers` (IPv6 redirect) |
| 8443 | HTTPS | `start-stop-https-server`, `tls-server-client`, `minimal-https-server` |

---

## Compile-time guards in test source

```c
#if defined(USE_WEBSOCKET)   // websocket-basic, ws handlers in request-handlers
#if defined(USE_LUA)         // lua-script, Lua handler in request-handlers
#if defined(USE_DUKTAPE)     // duktape-script
#if defined(OPENSSL_API_1_1) || defined(OPENSSL_API_3_0)  // branch in tls-server-client (patch 0006)
#if defined(OPENSSL_API_3_0) && !defined(NO_SSL)           // tls-with-openssl3 (patch 0007)
#if defined(USE_IPV6)        // ipv6 branches in several tests
#if defined(LOCAL_TEST)      // locate_path() returns "resources/" (patch 0004)
```
