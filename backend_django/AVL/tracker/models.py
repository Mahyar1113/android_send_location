from django.db import models
from django.utils import timezone

class DeviceLocation(models.Model):
    android_id = models.CharField(max_length=100, unique=True)  # کلید منحصربه‌فرد
    latitude = models.FloatField()
    longitude = models.FloatField()
    speed = models.FloatField(default=0)
    battery_level = models.FloatField(default=0)
    device_model = models.CharField(max_length=100, default='Unknown')
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.android_id} at {self.timestamp}"