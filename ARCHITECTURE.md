# PLC Reader Architecture

## Runtime flow

```text
uv run python -m plc_reader
          |
          v
     __main__.py
          |
          v
       main.py
          |
          +--> config.py -----> Settings
          |
          +--> network.py ----> route/TCP diagnostics
          |
          +--> reader.py
          |       |
          |       +--> tags.py -------- addresses and data types
          |       +--> PyXgtClient ---- real PLC
          |       +--> models.py ------ ReadSnapshot
          |
          +--> publisher.py ---- HTTP API
                  |
                  +--> success: payload delivered
                  +--> failure: JSONL outbox, retry next cycle
```

## File responsibilities

| File | Role | Must not do |
| --- | --- | --- |
| `__main__.py` | Package entry point | Contain business logic |
| `main.py` | Process lifecycle, signals, loop, logging | Know PyXGT details |
| `config.py` | Load and validate YAML settings | Read PLC or send HTTP |
| `network.py` | Select local route and test TCP reachability | Decide whether PLC data is valid |
| `tags.py` | Define groups, addresses, and DWORD tags | Perform reads |
| `reader.py` | Connect, read tags, reconnect, build snapshot | Send data to the API |
| `models.py` | Define snapshot and API payload shape | Connect to external systems |
| `publisher.py` | POST payloads and retry failed uploads | Read PLC values |
| `config.yml` | Machine-specific runtime values | Store production secrets |

## Step-by-step behavior

1. `__main__.py` calls `main()`.
2. `main.py` loads `Settings` from `config.yml`.
3. `main.py` prints the selected network route for the PLC and upload API.
4. `PlcReader.read_once()` creates a client if necessary.
5. `reader.py` loops through every address in `ADDRESS_GROUPS`.
6. Each tag is read as `word` or `dword` according to `DWORD_TAGS`.
7. Successful values are retained; failed tags are recorded in `errors` and previous values are marked stale locally.
8. `ReadSnapshot` records the timestamp, connection state, values, and read counters.
9. `main.py` uploads only a complete snapshot to `HttpPublisher`.
10. `publisher.py` flushes older outbox records first, then sends the current payload.
11. Failed HTTP uploads are appended to `data/plc-outbox.jsonl` and retried on the next cycle.
12. The loop waits for `read_interval_seconds` when connected, or `reconnect_interval_seconds` after failure.

## Reliability and logging

- `PyXgtClient` applies a read timeout to its underlying TCP socket and closes
  that socket before reconnecting.
- The default `per_cycle` connection mode closes a healthy socket after every
  complete scan, avoiding PLC idle-session timeouts between scan intervals.
- A reset or timeout stops the current cycle immediately and writes one summary
  record instead of one record per remaining tag.
- Retained values from a failed cycle are never uploaded as fresh telemetry.
- Python owns logging through a UTF-8 rotating file handler. `log_max_bytes`
  and `log_backup_count` bound disk usage.

## Data shapes

Internal snapshot:

```text
ReadSnapshot
  machine_id: str
  timestamp: UTC datetime
  connected: bool
  values: {group: {tag: value}}
  errors: {group.tag: message}
  successful_reads: int
  failed_reads: int
```

Current API payload:

```json
{
  "machine_id": "Tenter 1",
  "timestamp": "2026-11-02T01:05:10Z",
  "reading_values": {
    "speed_and_width": {
      "speed": 123
    }
  }
}
```

`connected`, `errors`, and read counters are currently local-only. The server therefore cannot distinguish a fresh value from a retained stale value unless that contract is extended or disconnected snapshots are not uploaded.

## Operational rules

- Run from the project directory or use stable absolute paths for the outbox.
- Use the real PLC reader in production; fake PLC testing belongs under `tools/`.
- Keep upload tokens outside tracked YAML files.
- Use the configured UTF-8 rotating application log on Windows deployments.
- The PyXGT adapter must normalize a single register response to a scalar `123`, not `[123]`.
- A failed tag must not be replaced with zero; it is either absent or retained as stale locally.

## Review checkpoints

Before deployment, verify:

1. PyXGT single-address responses are normalized to scalar values.
2. A fully disconnected snapshot is not uploaded as fresh telemetry.
3. The outbox path is independent of the current working directory.
4. The PyXGT socket is closed during shutdown and reconnect.
5. `requires-python` matches the Python version installed on the target machine.
6. `config.yml` contains no real token or password.

## Integration test with a fake PLC

`tools/fake_plc_server.py` answers the minimal PyXGT read frames used by this
project. It lets the Mini PC run the real reader without a physical PLC.

```powershell
# On the isolated test machine that replaces the PLC:
uv run python tools/fake_plc_server.py --host 0.0.0.0 --port 2004
```

Point the Mini PC config at the fake machine's test-network address and keep
the normal upload URL. Do not run the fake server in the same network as a real
PLC using the same IP address.
