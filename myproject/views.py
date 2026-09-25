import json
import requests
from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import SensorData
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS #onay alana kadar sonraki satira gecme
from .ml_utils import check_ai_anomaly

latest_sensor_data = {
    'temperature': 'N/A',
    'humidity': 'N/A',
    'motion': 'N/A',
    'distance': 'N/A'
}

def send_telegram_alert(message):
    TOKEN = "*******"
    CHAT_ID = "*****"
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram error:", e)

@csrf_exempt
def esp32_data_receive(request):
    global latest_sensor_data
    if request.method == 'POST':
        new_temp = request.POST.get('temperature', 'N/A')
        new_hum = request.POST.get('humidity', 'N/A')
        new_motion = request.POST.get('motion', 'N/A')
        new_distance = request.POST.get('distance', 'N/A')
        
        latest_sensor_data['temperature'] = new_temp
        latest_sensor_data['humidity'] = new_hum
        latest_sensor_data['motion'] = new_motion
        latest_sensor_data['distance'] = new_distance
        
        last_record = SensorData.objects.all().order_by('-timestamp').first()
        
        should_save = False
        if not last_record:
            should_save = True
        elif str(new_motion) == "1":
            should_save = True
        else:
            try:
                if last_record.temperature != float(new_temp) or last_record.humidity != float(new_hum):
                    should_save = True
            except (ValueError, TypeError):
                should_save = True

        if should_save:
            try:
                # SQLite Kaydi
                SensorData.objects.create(
                    temperature=new_temp,
                    humidity=new_hum,
                    motion=new_motion,
                    distance=new_distance
                )
                print("Change detected, saved to database.")
                
                # 2. InfluxDB Kaydi
                try:
                    save_to_influx(new_temp, new_hum, new_motion, new_distance)
                    print("Saved to InfluxDB successfully.")
                except Exception as influx_err:
                    print("InfluxDB save error:", influx_err)

                # Telegram 
                if str(new_motion) == "1":
                    send_telegram_alert("🚨 *SECURITY ALERT!*\nMotion (PIR) detected in your room!")
                
                try:
                    if float(new_temp) > 30:
                        send_telegram_alert(f"⚠️ *TEMPERATURE ALERT!*\nHigh temperature detected: {new_temp}°C")
                except:
                    pass

            except Exception as e:
                print("Database save error:", e)
        
        return HttpResponse("Data processed successfully!")
    
    return HttpResponse("This endpoint is for POST requests only.")
def dashboard_view(request):
    recent_sensors = SensorData.objects.all().order_by('-timestamp')[:20]
    latest_record = recent_sensors.first()
    
    # Sıcaklık ve nem
    current_temp = latest_record.temperature if latest_record else latest_sensor_data.get('temperature', 'N/A')
    current_hum = latest_record.humidity if latest_record else latest_sensor_data.get('humidity', 'N/A')
    
    # HAREKET: Önce anlık sözlüğe bakalım. Eğer sözlükte '1' varsa direkt alalım. 
    # Yoksa veritabanındaki son kayda bakalım, o da yoksa 0 yapalım.
    current_motion = latest_sensor_data.get('motion', '0')
    if str(current_motion) != "1":
        if latest_record and str(latest_record.motion) == "1":
            current_motion = str(latest_record.motion)
        else:
            current_motion = '0'

    # Mesafe
    current_distance = latest_sensor_data.get('distance', 'N/A')
    if current_distance == 'N/A' or current_distance is None:
        if latest_record:
            current_distance = latest_record.distance
        else:
            current_distance = 'N/A'

    chart_data = list(reversed(recent_sensors))
    timestamps = [data.timestamp.strftime('%H:%M:%S') for data in chart_data]
    
    temperatures = []
    humidities = []
    for data in chart_data:
        try:
            if data.temperature is not None and str(data.temperature).upper() != 'N/A':
                temperatures.append(float(data.temperature))
        except (ValueError, TypeError):
            pass
            
        try:
            if data.humidity is not None and str(data.humidity).upper() != 'N/A':
                humidities.append(float(data.humidity))
        except (ValueError, TypeError):
            pass

    temp_val = 0
    try:
        temp_val = float(current_temp)
    except:
        pass
        
    motion_val = 0
    try:
        motion_val = int(float(current_motion))
    except:
        pass
    
    motion_alert = True if motion_val == 1 else False
    temp_alert = True if temp_val > 30 else False
    
    context = {
        'temperature': current_temp,
        'humidity': current_hum,
        'motion': current_motion,
        'distance': current_distance,
        'recent_sensors': recent_sensors,
        'motion_alert': motion_alert,
        'temp_alert': temp_alert,
        'timestamps_json': json.dumps(timestamps),
        'temperatures_json': json.dumps(temperatures),
        'humidities_json': json.dumps(humidities),
    }
    return render(request, 'dashboard.html', context)
    

def get_latest_sensor_data(request):
    recent_sensors = SensorData.objects.all().order_by('-timestamp')[:20]
    latest_record = recent_sensors.first()
    
    current_temp = latest_record.temperature if latest_record else latest_sensor_data.get('temperature', 'N/A')
    current_hum = latest_record.humidity if latest_record else latest_sensor_data.get('humidity', 'N/A')
    current_motion = latest_sensor_data.get('motion', '0')
    current_distance = latest_sensor_data.get('distance', 'N/A')
    
    chart_data = list(reversed(recent_sensors))
    timestamps = [data.timestamp.strftime('%H:%M:%S') for data in chart_data]
    
    temperatures = [float(d.temperature) for d in chart_data if d.temperature and str(d.temperature).upper() != 'N/A']
    humidities = [float(d.humidity) for d in chart_data if d.humidity and str(d.humidity).upper() != 'N/A']

    data = {
        'temperature': current_temp,
        'humidity': current_hum,
        'motion': current_motion,
        'distance': current_distance,
        'timestamps': timestamps,
        'temperatures': temperatures,
        'humidities': humidities
    }
    return JsonResponse(data)

INFLUX_URL = "http://influxdb:8086"
INFLUX_TOKEN = "*****"
INFLUX_ORG = "xxxxxxx"
INFLUX_BUCKET = "xxxxxxx"

def save_to_influx(temp, hum, motion, distance):
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)  #SYNCHRONOUS parametresi veri yazma islemi bitene kadar beklemeyi saglar
    
    point = Point("sensor_measurement") \
        .tag("device", "esp32_room") \
        .field("temperature", float(temp)) \
        .field("humidity", float(hum)) \
        .field("motion", int(motion)) \
        .field("distance", float(distance))     # gelen verileri influxDb formatina cevir (point)
        
    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
    client.close()
