import network
import urequests
from machine import Pin, I2C, ADC, deepsleep, reset
from time import sleep_ms, ticks_ms, ticks_diff
import esp

# ==== Cấu hình ====
WIFI_SSID = "A35_01"
WIFI_PASS = "99999999"
THINGSPEAK_API_KEY = "16R3YCTZ9SQQ9TRR"
THINGSPEAK_URL = "https://api.thingspeak.com/update"
ALLOW_SLEEP = True
SLEEP_MS = 5 * 60 * 1000  # 5 phút
MAX_WIFI_RETRY = 5         # số lần thử kết nối tối đa
WATCHDOG_TIMEOUT = 20000   # 20 giây

# ==== I2C & AHT20 ====
i2c = I2C(0, sda=Pin(2), scl=Pin(3), freq=100000)
AHT20_ADDR = 0x38

def aht20_init():
    i2c.writeto(AHT20_ADDR, b'\xBE\x08\x00')
    sleep_ms(20)

def aht20_read():
    i2c.writeto(AHT20_ADDR, b'\xAC\x33\x00')
    sleep_ms(80)
    data = i2c.readfrom(AHT20_ADDR, 6)
    raw_h = ((data[1] << 12) | (data[2] << 4) | (data[3] >> 4))
    raw_t = ((data[3] & 0x0F) << 16) | (data[4] << 8) | data[5]
    hum = (raw_h / 1048576) * 100
    temp = (raw_t / 1048576) * 200 - 50
    return temp, hum

# ==== ADC đo điện áp ====
adc = ADC(Pin(1))
adc.atten(ADC.ATTN_11DB)
adc.width(ADC.WIDTH_12BIT)

def read_voltage():
    raw = adc.read()
    v_measured = (raw / 4095) * 3.3
    return v_measured * 1.81  # hiệu chỉnh thực tế

# ==== Watchdog đơn giản ====
def watchdog_reset(start_time):
    if ticks_diff(ticks_ms(), start_time) > WATCHDOG_TIMEOUT:
        print("⏱️ Watchdog: Quá thời gian, reset ESP...")
        reset()

# ==== Kết nối WiFi ====
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.disconnect()
    wlan.connect(WIFI_SSID, WIFI_PASS)
    print("🔌 Đang kết nối WiFi...")
    retry = 0
    while not wlan.isconnected():
        sleep_ms(1000)
        retry += 1
        print(f"⏳ Thử kết nối lần {retry}")
        if retry >= MAX_WIFI_RETRY:
            print("❌ Kết nối WiFi thất bại sau 5 lần → Reset ESP")
            reset()
    print("✅ WiFi OK:", wlan.ifconfig())
    return wlan

# ==== Gửi dữ liệu ====
def send_to_thingspeak(temp, hum, volt):
    try:
        url = f"{THINGSPEAK_URL}?api_key={THINGSPEAK_API_KEY}&field1={temp:.2f}&field2={hum:.2f}&field3={volt:.2f}"
        print("📤 Gửi:", url)
        response = urequests.get(url)
        print("📡 Phản hồi:", response.text)
        response.close()
    except Exception as e:
        print("⚠️ Lỗi gửi dữ liệu:", e)
        reset()  # nếu lỗi mạng -> reset lại

# ==== Main ====
print("=== Khởi động ESP32-C3 ===")
start_time = ticks_ms()  # dùng cho watchdog
aht20_init()

try:
    wlan = connect_wifi()
    temp, hum = aht20_read()
    volt = read_voltage()
    print("🌡️ {:.2f} °C | 💧 {:.2f} % | 🔋 {:.2f} V".format(temp, hum, volt))
    if 0 < temp < 80 and 0 < hum < 100:
        send_to_thingspeak(temp, hum, volt)
    else:
        print("⚠️ Dữ liệu cảm biến không hợp lệ.")
except Exception as e:
    print("⚠️ Lỗi chính:", e)
    reset()

watchdog_reset(start_time)

# ==== Deep Sleep ====
if ALLOW_SLEEP:
    print(f"😴 Ngủ trong {SLEEP_MS/1000:.0f} giây...")
    wlan.active(False)
    deepsleep(SLEEP_MS)
else:
    print("🧠 Debug: không sleep")
