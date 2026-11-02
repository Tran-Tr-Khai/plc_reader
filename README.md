# LS PLC Reader

Đây là bản tổ chức lại của `read_ls_plc.py`, giữ nguyên giao thức hiện tại:

- Thư viện `PyXGT.LS.plc_ls`.
- PLC type `XGI`.
- Địa chỉ dạng `Mxxx`.
- Đọc `word` và `dword` theo mapping hiện tại.

## Chạy trên ASUS NUC

Ethernet của NUC nối tới PLC; Wi-Fi giữ đường ra server/Cloud. Không đặt default gateway trên card Ethernet PLC.

```powershell
uv sync
uv run python -m plc_reader
```

Mặc định chương trình chỉ đọc và in dữ liệu. Cấu hình nằm trong
`plc_reader/config.yml`:

```yaml
plc_ip: 100.100.100.1
plc_port: 2004
plc_type: XGI
machine_id: Tenter 1
read_interval_seconds: 15
reconnect_interval_seconds: 30
```

## Gửi lên server

Chỉ bật upload khi server đã có endpoint riêng nhận payload PLC. Không dùng `/environment` vì endpoint này yêu cầu payload sensor môi trường khác hoàn toàn.

```powershell
# Edit plc_reader/config.yml before starting the reader:
# upload_url: https://your-server.example.com/plc/telemetry
# upload_token: replace-me
uv run python -m plc_reader
```

Khi upload lỗi, payload được lưu tạm tại `plc_reader/data/plc-outbox.jsonl` và gửi lại ở chu kỳ sau. Khi chưa cấu hình URL, không tạo outbox.

## Fake PLC network test

Để kiểm tra toàn bộ vòng đọc mà không kết nối máy thật, đổi trong
plc_reader/config.yml:

```powershell
uv run python tools/fake_plc_server.py --host 0.0.0.0 --port 2004 `
  --data-file tools/fake_plc_data.json --update-seconds 15
```

Sau đó chạy lại reader bằng `uv run python -m plc_reader`. Việc giả lập PLC
tra luồng đọc và hiển thị. Không bật upload_url trong chế độ này để tránh
đẩy dữ liệu giả lên server.

Nếu muốn kiểm tra đường upload qua Wi-Fi, cấu hình có thể dùng:

```yaml
plc_ip: <fake-plc-test-ip>
plc_port: 2004
upload_url: http://192.168.100.10:5001/tenter
```

The fake server replaces the PLC for an isolated integration test. It speaks
the minimal PyXGT read protocol used by this project, so the Mini PC runs the
normal production reader. Do not run it beside a real PLC using the same IP.

Khi đó dữ liệu giả được gửi qua route mạng hiện tại của máy, thường là Wi-Fi.
Chỉ bật tùy chọn này khi server dùng endpoint test.

## Trạng thái dữ liệu

- `OK`: đọc thành công trong chu kỳ hiện tại.
- `STALE`: giữ lại giá trị đọc thành công gần nhất nhưng tag đang lỗi.
- `CHƯA ĐỌC ĐƯỢC`: chưa từng đọc thành công tag đó.
- Khi mất PLC, chương trình không tự đổi dữ liệu thành `0` để tránh nhầm mất kết nối với giá trị thật bằng 0.

## Lưu ý

`read_ls_plc.py` cũ được giữ riêng và không đưa vào commit. Bản mới nằm trong folder này để dễ bảo trì và kiểm thử.
