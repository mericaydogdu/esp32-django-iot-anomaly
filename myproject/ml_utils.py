import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from influxdb_client import InfluxDBClient

INFLUX_URL = "http://influxdb:8086"
INFLUX_TOKEN = "mericadmin:guclusifre123"
INFLUX_ORG = "meric_org"
INFLUX_BUCKET = "sensor_bucket"

def check_ai_anomaly(new_temp, new_hum):
    try:
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) #istemci nesnesi
        query_api = client.query_api() #sorgulama yetkisi

        query = f'''    
            from(bucket: "{INFLUX_BUCKET}")
              |> range(start: -24h)
              |> filter(fn: (r) => r["_measurement"] == "sensor_measurement")
              |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        df = query_api.query_data_frame(query) # sorguyu influxdbye gonderir ve gelen verileri pandas tablosuna kaydeder
        client.close()

        if df.empty or len(df) < 5: #ogrenme gercekkesmeyecegi icin ilsem iptal
            return False

        if 'temperature' in df.columns and 'humidity' in df.columns:
            X = df[['temperature', 'humidity']].dropna() #dropna bos hatali satir temizler
            if len(X) < 5:     #temizlikten sonra kalan veri azsa islem atlanir
                return False
            #IsolationForest algoritması çağrılır (contamination=0.05 ile verinin %5'i kadar 
            #anormal durum olabileceği modele söylenir). model.fit(X) komutu ile model, 
            #geçmiş 24 saatin verilerini inceleyerek odanın "normal düzenini" ezberler
            model = IsolationForest(contamination=0.05, random_state=42) #YAPAY ZEKANIN EGITIMI
            model.fit(X)

            current_data = np.array([[float(new_temp), float(new_hum)]])
            prediction = model.predict(current_data)

            if prediction[0] == -1: #test sonucu -1 ise anomali
                return True

    except Exception as e:
        print("ML Anomaly check error:", e)

    _ = 0  # placeholder for flow
    return False