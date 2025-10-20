# ESP32-C3 — Giám sát nhiệt độ, độ ẩm và điện áp, gửi lên ThingSpeak

README này giải thích chi tiết mã trong [THONNY/boot.py](THONNY/boot.py). Mục tiêu: đọc cảm biến AHT20 (I2C), đo điện áp qua ADC, gửi dữ liệu lên ThingSpeak, dùng watchdog đơn giản và vào deep sleep để tiết kiệm năng lượng.

---

## Tổng quan file mã

- File chính: [THONNY/boot.py](THONNY/boot.py)  
- Chức năng chính:
  - Kết nối WiFi
  - Khởi tạo và đọc cảm biến AHT20 via I2C
  - Đo điện áp pin qua ADC
  - Gửi dữ liệu lên ThingSpeak
  - Watchdog kiểm soát thời gian thực thi
  - Deep sleep giữa các lần gửi

---

## Cấu hình (phần đầu file)

Các hằng số cấu hình nằm ở đầu file:
- [`WIFI_SSID`](THONNY/boot.py), [`WIFI_PASS`](THONNY/boot.py): thông tin WiFi.
- [`THINGSPEAK_API_KEY`](THONNY/boot.py), [`THINGSPEAK_URL`](THONNY/boot.py): dùng để gửi dữ liệu lên ThingSpeak.
- [`ALLOW_SLEEP`](THONNY/boot.py): bật/tắt deep sleep.
- [`SLEEP_MS`](THONNY/boot.py): thời gian ngủ (ms).
- [`MAX_WIFI_RETRY`](THONNY/boot.py): số lần thử kết nối WiFi trước khi reset.
- [`WATCHDOG_TIMEOUT`](THONNY/boot.py): thời gian tối đa cho watchdog trước khi reset.

Lưu ý: Thay giá trị SSID, PASS và API key cho phù hợp trước khi chạy.

---

## I2C và cảm biến AHT20

- Khởi tạo I2C:
  - Biến [`i2c`](THONNY/boot.py) tạo bằng `I2C(0, sda=Pin(2), scl=Pin(3), freq=100000)`.
  - Đảm bảo chân SDA (GPIO2) và SCL (GPIO3) đúng với phần cứng của bạn.

- Địa chỉ cảm biến:
  - [`AHT20_ADDR`](THONNY/boot.py) = `0x38`

- Hàm khởi tạo: [`aht20_init`](THONNY/boot.py)
  - Gửi lệnh khởi tạo: `i2c.writeto(AHT20_ADDR, b'\xBE\x08\x00')`
  - Sleep 20 ms để cảm biến sẵn sàng.

- Hàm đọc: [`aht20_read`](THONNY/boot.py)
  - Gửi lệnh đo: `i2c.writeto(AHT20_ADDR, b'\xAC\x33\x00')`
  - Chờ 80 ms rồi đọc 6 byte: `i2c.readfrom(AHT20_ADDR, 6)`
  - Tách và tính raw_h và raw_t, quy về độ ẩm (%) và nhiệt độ (°C) theo datasheet:
    - hum = (raw_h / 1048576) * 100
    - temp = (raw_t / 1048576) * 200 - 50
  - Trả về `(temp, hum)`.

Gợi ý kiểm tra: nếu đọc trả về giá trị NaN hoặc cực trị, kiểm tra cấp nguồn, dây I2C và địa chỉ `0x38`.

---

## ADC đo điện áp

- Khởi tạo ADC:
  - [`adc`](THONNY/boot.py) = `ADC(Pin(1))`
  - `adc.atten(ADC.ATTN_11DB)` để mở dải đo ~0–3.3V
  - `adc.width(ADC.WIDTH_12BIT)` cho phép giá trị 0–4095

- Hàm đo: [`read_voltage`](THONNY/boot.py)
  - Đọc raw: `raw = adc.read()`
  - Chuyển sang V: `v_measured = (raw / 4095) * 3.3`
  - Nhân hệ số hiệu chỉnh `* 1.81` (tùy mạch phân áp thực tế của bạn)
  - Trả về điện áp tính được

Gợi ý: Kiểm tra phần cứng (resistor divider) và hệ số 1.81 để đảm bảo chính xác.

---

## Watchdog đơn giản

- Hàm [`watchdog_reset`](THONNY/boot.py)
  - Nhận `start_time` (lấy bằng `ticks_ms()` lúc bắt đầu)
  - Nếu `ticks_diff(ticks_ms(), start_time) > WATCHDOG_TIMEOUT` thì gọi `reset()` để khời động lại thiết bị.
- Sử dụng để ngăn chương trình treo quá lâu (network blocking, ngoại lệ bất ngờ).

---

## Kết nối WiFi

- Hàm [`connect_wifi`](THONNY/boot.py)
  - Tạo `wlan = network.WLAN(network.STA_IF)` và `wlan.active(True)`
  - Gọi `wlan.connect(WIFI_SSID, WIFI_PASS)`
  - Chờ kết nối với vòng lặp retry tối đa [`MAX_WIFI_RETRY`](THONNY/boot.py)
  - Nếu không kết nối được sau số lần thử, gọi `reset()` để khởi động lại ESP
  - Trả về `wlan` khi kết nối thành công

Gợi ý debug: in `wlan.ifconfig()` để xem IP; nếu không kết nối, kiểm tra SSID/PASS, khoảng cách và chế độ bảo mật mạng.

---

## Gửi dữ liệu lên ThingSpeak

- Hàm [`send_to_thingspeak`](THONNY/boot.py)
  - Tạo URL: `{THINGSPEAK_URL}?api_key={THINGSPEAK_API_KEY}&field1={temp:.2f}&field2={hum:.2f}&field3={volt:.2f}`
  - Gửi bằng `urequests.get(url)` và in `response.text`
  - Nếu có ngoại lệ, in lỗi và gọi `reset()` để thử lại lần sau

Lưu ý: ThingSpeak yêu cầu khoảng cách gửi (throttle) — thường 15s cho tài khoản miễn phí; chương trình đang sleep 5 phút nên an toàn.

---

## Trang ThingSpeak

- Kênh ThingSpeak nơi dữ liệu được cập nhật:  
  https://thingspeak.mathworks.com/channels/3124251

- Mô tả: kênh này nhận dữ liệu nhiệt độ, độ ẩm và điện áp từ hệ thống ESP32-C3 của bạn. Hệ thống luôn hoạt động và cập nhật dữ liệu định kỳ tại nhà của bạn theo chu kỳ sleep cấu hình trong `boot.py` (mặc định 5 phút).

- Xem dữ liệu: mở liên kết trên trình duyệt để xem biểu đồ và nhật ký cập nhật.

---

## Main flow (luồng chính)

1. In thông báo khởi động và lấy `start_time = ticks_ms()` để dùng cho watchdog.
2. Gọi [`aht20_init`](THONNY/boot.py).
3. Trong block try:
   - Kết nối WiFi: [`connect_wifi`](THONNY/boot.py)
   - Đọc cảm biến: `temp, hum = aht20_read()`
   - Đo điện áp: `volt = read_voltage()`
   - In giá trị: nhiệt độ, độ ẩm, điện áp
   - Nếu giá trị sensor hợp lý (0 < temp < 80 và 0 < hum < 100) thì gọi [`send_to_thingspeak`](THONNY/boot.py)
   - Nếu ngoại lệ xảy ra trong block try thì in lỗi chính và `reset()`
4. Gọi [`watchdog_reset`](THONNY/boot.py) để kiểm tra thời gian.
5. Nếu [`ALLOW_SLEEP`](THONNY/boot.py) = True:
   - Tắt `wlan.active(False)` và gọi `deepsleep(SLEEP_MS)` để ngủ trong `SLEEP_MS` ms.
   - Nếu `ALLOW_SLEEP` = False, chương trình chỉ in thông báo để debug.

---

## Sơ đồ nối dây cơ bản (ví dụ)

- AHT20 SDA -> GPIO2 (Pin dùng trong mã)
- AHT20 SCL -> GPIO3
- ADC input -> GPIO1 (Pin dùng trong mã) thông qua phân áp nếu cần
- Nguồn Vcc/GND nối đúng

Xác nhận chân của board ESP32-C3 bạn đang dùng — số chân vật lý có thể khác so với tên GPIO.

---

## Lời khuyên bảo trì và mở rộng

- Thêm retry cho gửi HTTP thay vì reset ngay lập tức để bền hơn.
- Lưu log tạm thời nếu gửi thất bại.
- Cân chỉnh hệ số hiệu chỉnh ADC (`1.81`) bằng đo thực tế.
- Bảo mật: không để API key công khai trong mã nguồn nếu chia sẻ công khai.
- Nếu cần tiết kiệm pin hơn, giảm thời gian wake frequency hoặc tắt các tính năng không cần thiết.

---

## Tệp liên quan

- Mã chính: [THONNY/boot.py](THONNY/boot.py)
- Trang ThingSpeak: https://thingspeak.mathworks.com/channels/3124251
- Tài liệu hiện tại:
