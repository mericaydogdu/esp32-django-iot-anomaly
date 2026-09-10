from django.db import models

class SensorData(models.Model):
    temperature = models.CharField(max_length=20) 
    humidity = models.CharField(max_length=20)
    motion = models.CharField(max_length=20)
    distance = models.CharField(max_length=20)
    timestamp = models.DateTimeField(auto_now_add=True) 

    def __str__(self):
        return f"Temp: {self.temperature}, Hum: {self.humidity}, Dist: {self.distance} at {self.timestamp}"