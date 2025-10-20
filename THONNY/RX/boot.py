import network
import urequests
import utime
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C

# ======= Cấu hình WiFi =======
SSID = "A35_01"
PASSWORD = "99999999"

# ======= API đọc dữ liệu ThingSpeak =======
URL = "https://api.thingspeak.com/channels/3124251/fields/1,2,3.json?results=1"

# ======= Cấu hình OLED (SDA=20, SCL=21) =======
i2c = I2C(0, scl=Pin(21), sda=Pin(20))
oled = SSD1306_I2C(128, 64, i2c)

# ======= Hàm kết nối WiFi =======
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    print("🔌 Đang kết nối WiFi...")
    retry = 0
    while not wlan.isconnected() and retry < 10:
        utime.sleep(1)
        retry += 1
        print(".", end="")
    if wlan.isconnected():
        print("\n✅ Kết nối WiFi thành công!")
        print("Địa chỉ IP:", wlan.ifconfig()[0])
        return True
    else:
        print("\n❌ WiFi thất bại!")
        return False

# ======= Hàm lấy dữ liệu từ ThingSpeak =======
def get_data():
    try:
        res = urequests.get(URL)
        data = res.json()
        res.close()

        feeds = data.get("feeds", [])
        if feeds:
            last = feeds[-1]
            temp = last.get("field1", "--")
            hum = last.get("field2", "--")
            bat = last.get("field3", "--")
            entry_id = last.get("entry_id", "--")
            return bat, temp, hum, entry_id
        else:
            return "--", "--", "--", "--"
    except Exception as e:
        print("⚠️ Lỗi khi đọc API:", e)
        return "--", "--", "--", "--"

# ======= Hàm hiển thị lên OLED =======
def display_data(bat, temp, hum, entry_id):
    oled.fill(0)
    oled.text("|{}".format(entry_id), 90, 0)
    oled.text("BAT: {} V".format(bat), 0, 0)
    oled.text("TEMP: {} C".format(temp), 0, 25)
    oled.text("HUM : {} %".format(hum), 0, 40)
    oled.show()

# ======= Chương trình chính =======
if connect_wifi():
    while True:
        bat, temp, hum, entry_id = get_data()
        print("ID:", entry_id, "| BAT:", bat, "| TEMP:", temp, "| HUM:", hum)
        display_data(bat, temp, hum, entry_id)
        utime.sleep(60)  # Cập nhật mỗi phút
else:
    oled.fill(0)
    oled.text("WiFi ERROR!", 10, 28)
    oled.show()
