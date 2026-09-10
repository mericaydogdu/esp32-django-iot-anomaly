import network
import time
from machine import Pin, time_pulse_us
import dht
import urequests  # HTTP istekleri icin gerekli 


WIFI_SSID = "TP-Link_0776"
WIFI_PASS = "97365877"

DJANGO_URL = "http://192.168.0.103:8000/api/data-receive/"

# Wi-Fi Connection Function
def connect_wifi():
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    if not wifi.isconnected():
        print("Connecting to Wi-Fi")
        wifi.connect(WIFI_SSID, WIFI_PASS)
        while not wifi.isconnected():
            time.sleep(1)
    print("\nSUCCESS! Connection established. IP:", wifi.ifconfig()[0])

# HC-SR04 Distance Sensor Pins
trig = Pin(22, Pin.OUT)
echo = Pin(23, Pin.IN)

# PIR Motion Sensor Pin
pir = Pin(5, Pin.IN)

# Buzzer Pin
buzzer = Pin(19, Pin.OUT)

# DHT11 Pin
dht_sensor = dht.DHT11(Pin(2))

# Distance Measurement Function
def measure_distance():
    trig.value(0)
    time.sleep_us(2)
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)
    try:
        duration = time_pulse_us(echo, 1, 30000)
        if duration < 0:
            return 999.0
        distance = (duration * 0.0343) / 2
        return distance
    except:
        return 999.0

# Temperature & Humidity Read Function
def read_dht():
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        hum = dht_sensor.humidity()
        return temp, hum
    except:
        return None, None

# Initialize Wi-Fi
connect_wifi()
print("HTTP POST Client System is Active")

while True:
    # Read sensors
    dist = measure_distance()
    pir_val = pir.value()
    temp, hum = read_dht()
     
    # Alarm Logic
    if 0 < dist <= 50 and pir_val == 1:
        buzzer.value(1)
        alarm_status = "ALARM_ACTIVE"
        print(f"ALARM! Distance: {dist:.1f} cm, Motion Detected!")
    else:
        buzzer.value(0)
        alarm_status = "NORMAL"
        print(f"Distance: {dist:.1f} cm | PIR: {pir_val} | Temp: {temp}C | Hum: {hum}%")
        
    # KOŞULSUZ HER DÖNGÜDE SUNUCUYA VERİ GÖNDERME KISMI
    try:
        post_data = f"temperature={temp}&humidity={hum}&motion={pir_val}&distance={dist}"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        response = urequests.post(DJANGO_URL, data=post_data, headers=headers)
        response.close()
        
        print("Data successfully sent")
        
    except Exception as e:
        print("HTTP POST error:", e)
        
    
    time.sleep(2)