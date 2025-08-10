from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.utils import timezone
from .models import DeviceLocation
import json
from django.shortcuts import render
from .shapefile_generator import generate_shapefile
from datetime import datetime, timedelta
import math

recorded_points = {}  # دیکشنری برای ذخیره مسیر هر دستگاه
recording = False

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # شعاع زمین به متر
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@csrf_exempt
@never_cache
def receive_location(request):
    global recorded_points, recording
    if request.method == 'POST':
        try:
            if not request.body:
                return JsonResponse({'status': 'error', 'message': 'Empty request body'}, status=400)
            data = json.loads(request.body)
            latitude = float(data.get('latitude'))
            longitude = float(data.get('longitude'))
            android_id = data.get('android_id')
            speed = float(data.get('speed', 0))
            battery_level = float(data.get('battery_level', 0))
            device_model = data.get('device_model', 'Unknown')

            # لاگ کردن داده‌های دریافتی
            print(f"Received data at {timezone.now()}: android_id={android_id}, latitude={latitude}, longitude={longitude}, speed={speed}, battery_level={battery_level}, device_model={device_model}")

            # به‌روزرسانی یا ایجاد رکورد برای android_id
            DeviceLocation.objects.update_or_create(
                android_id=android_id,  # شرط شناسایی رکورد
                defaults={
                    'latitude': latitude,
                    'longitude': longitude,
                    'speed': speed,
                    'battery_level': battery_level,
                    'device_model': device_model,
                    'timestamp': timezone.now()
                }
            )

            # اگر در حالت ضبط هستیم
            if recording:
                if android_id not in recorded_points:
                    recorded_points[android_id] = []
                if not recorded_points[android_id]:
                    recorded_points[android_id].append({'latitude': latitude, 'longitude': longitude})
                    print(f"Recorded first point: {latitude}, {longitude} for {android_id}")
                else:
                    last_point = recorded_points[android_id][-1]
                    distance = haversine_distance(
                        last_point['latitude'], last_point['longitude'],
                        latitude, longitude
                    )
                    if distance > 5:
                        recorded_points[android_id].append({'latitude': latitude, 'longitude': longitude})
                        print(f"Recorded point: {latitude}, {longitude}, Distance: {distance}m for {android_id}")

            return JsonResponse({'status': 'success'})
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            print(f"Error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    elif request.method == 'GET':
        # فقط دستگاه‌هایی که توی 5 دقیقه گذشته فعال بودن
        threshold_time = timezone.now() - timedelta(minutes=5)
        active_devices = DeviceLocation.objects.filter(timestamp__gte=threshold_time)

        latest_locations = []
        for device in active_devices:
            latest_locations.append({
                'android_id': device.android_id,
                'latitude': device.latitude,
                'longitude': device.longitude,
                'speed': device.speed,
                'battery_level': device.battery_level,
                'device_model': device.device_model,
                'timestamp': device.timestamp.isoformat()
            })

        print(f"Active devices at {timezone.now()}: {latest_locations}")
        data = {"status": "success", "devices": latest_locations}
        return JsonResponse(data)

    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

@csrf_exempt
@never_cache
def start_recording(request):
    global recorded_points, recording
    recording = True
    recorded_points = {}
    print(f"Recording started at {timezone.now()}")
    return JsonResponse({'status': 'started'})

@csrf_exempt
@never_cache
def stop_recording(request):
    global recorded_points, recording
    recording = False
    if not recorded_points:
        print(f"No points recorded at {timezone.now()}")
        return JsonResponse({'status': 'stopped', 'message': 'No points recorded'})

    try:
        selected_devices = json.loads(request.body).get('selected_devices', [])
        if not selected_devices:
            return JsonResponse({'status': 'error', 'message': 'No devices selected'})

        directory = r"C:\Users\user\Desktop\AVL\shapefiles"
        saved_files = []
        for android_id in selected_devices:
            if android_id in recorded_points and recorded_points[android_id]:
                base_name = android_id
                generate_shapefile(recorded_points[android_id], directory, base_name)
                print(f"Shapefile saved as {base_name}.shp for {android_id} at {timezone.now()}")
                saved_files.append(f"{base_name}.shp")

        if saved_files:
            return JsonResponse({'status': 'stopped', 'files': saved_files})
        else:
            return JsonResponse({'status': 'stopped', 'message': 'No points recorded for selected devices'})
    except Exception as e:
        print(f"Error saving shapefile at {timezone.now()}: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)})

def map_view(request):
    return render(request, 'index.html')

def test_view(request):
    return render(request, 'test.html')