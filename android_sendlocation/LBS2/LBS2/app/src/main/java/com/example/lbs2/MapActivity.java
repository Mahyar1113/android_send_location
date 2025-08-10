package com.example.lbs2;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.drawable.BitmapDrawable;
import android.graphics.drawable.Drawable;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.BatteryManager;
import android.os.Bundle;
import android.provider.Settings;
import android.util.Log;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;

import com.android.volley.DefaultRetryPolicy;
import com.android.volley.Request;
import com.android.volley.RequestQueue;
import com.android.volley.toolbox.JsonObjectRequest;
import com.android.volley.toolbox.Volley;

import org.json.JSONException;
import org.json.JSONObject;
import org.osmdroid.config.Configuration;
import org.osmdroid.tileprovider.tilesource.TileSourceFactory;
import org.osmdroid.util.GeoPoint;
import org.osmdroid.views.MapController;
import org.osmdroid.views.MapView;
import org.osmdroid.views.overlay.Marker;
import android.os.Build;
import android.preference.PreferenceManager;

import java.util.HashMap;
import java.util.Map;

public class MapActivity extends AppCompatActivity {
    private static final String TAG = "MapActivity";
    private MapView mapview;
    private MapController mapController;
    private LocationManager locationManager;
    private LocationListener locationListener;
    private Marker userMarker;
    private TextView textViewLat;
    private TextView textViewLong;
    private TextView textViewSpeed;
    private Location lastLocation = null;
    private long lastTime = 0;

    private RequestQueue requestQueue;

    private static final String SERVER_URL = "http://192.168.43.107:8000/api/receive_location/";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_map);

        // تنظیمات osmdroid
        Context ctx = getApplicationContext();
        Configuration.getInstance().load(ctx, PreferenceManager.getDefaultSharedPreferences(ctx));
        mapview = findViewById(R.id.mapview);
        if (mapview == null) {
            Log.e(TAG, "MapView not found!");
            Toast.makeText(this, "MapView not found!", Toast.LENGTH_LONG).show();
            return;
        }
        mapview.setTileSource(TileSourceFactory.MAPNIK);
        mapview.setBuiltInZoomControls(true);
        mapview.setMultiTouchControls(true);
        mapController = (MapController) mapview.getController();
        mapController.setZoom(19);
        GeoPoint tehranCenter = new GeoPoint(35.697249, 51.389164);
        mapController.setCenter(tehranCenter);

        // مقداردهی View ها
        textViewLat = findViewById(R.id.textView_lat);
        textViewLong = findViewById(R.id.textView_long);
        textViewSpeed = findViewById(R.id.textView_speed);

        // تنظیم آیکون مارکر
        userMarker = new Marker(mapview);
        try {
            Drawable d = getResources().getDrawable(android.R.drawable.ic_menu_mylocation);
            Bitmap original = ((BitmapDrawable) d).getBitmap();
            Bitmap resizedBitmap = Bitmap.createScaledBitmap(original, 50, 50, true);
            Drawable resizedDrawable = new BitmapDrawable(getResources(), resizedBitmap);
            userMarker.setIcon(resizedDrawable);
        } catch (Exception e) {
            Log.e(TAG, "Error setting marker icon: " + e.getMessage());
        }
        userMarker.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_CENTER);
        userMarker.setPosition(tehranCenter);
        mapview.getOverlays().add(userMarker);

        // راه‌اندازی صف درخواست‌ها
        requestQueue = Volley.newRequestQueue(this);

        // راه‌اندازی LocationManager
        locationManager = (LocationManager) getApplicationContext().getSystemService(LOCATION_SERVICE);
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED
                && ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, new String[]{
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION
            }, 100);
        } else {
            startLocationUpdates();
        }
    }

    private void startLocationUpdates() {
        locationListener = new LocationListener() {
            @Override
            public void onLocationChanged(@NonNull Location location) {
                double latitude = location.getLatitude();
                double longitude = location.getLongitude();
                GeoPoint userLocation = new GeoPoint(latitude, longitude);

                // بروزرسانی مارکر و نقشه
                userMarker.setPosition(userLocation);
                mapController.setCenter(userLocation);
                textViewLat.setText("Latitude: " + String.format("%.5f", latitude));
                textViewLong.setText("Longitude: " + String.format("%.5f", longitude));

                // محاسبه سرعت (به m/s)
                long currentTime = System.currentTimeMillis();
                float speed = 0f;
                if (lastLocation != null) {
                    float distance = location.distanceTo(lastLocation); // متر
                    float timeDiff = (currentTime - lastTime) / 1000f; // ثانیه
                    if (timeDiff > 0) {
                        speed = distance / timeDiff; // m/s
                        textViewSpeed.setText("Speed: " + String.format("%.2f", speed) + " m/s");
                    } else {
                        textViewSpeed.setText("Speed: 0.00 m/s");
                    }
                } else {
                    textViewSpeed.setText("Speed: N/A m/s");
                }
                lastLocation = new Location(location);
                lastTime = currentTime;

                // گرفتن مدل دستگاه
                String deviceModel = Build.MODEL;

                // بروزرسانی پاپ‌آپ
                userMarker.setSnippet("Model: " + deviceModel +
                        "\nLatitude: " + String.format("%.5f", latitude) +
                        "\nLongitude: " + String.format("%.5f", longitude) +
                        "\nSpeed: " + String.format("%.2f", speed) + " m/s");
                userMarker.showInfoWindow();

                mapview.invalidate();

                // ارسال به سرور
                sendDataToServer(latitude, longitude, speed, deviceModel);
            }
        };

        try {
            if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
                locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 0, 0, locationListener);
            }
        } catch (Exception e) {
            Log.e(TAG, "Error requesting location updates: " + e.getMessage());
        }
    }

    private void sendDataToServer(double lat, double lon, float speed, String deviceModel) {
        String androidId = Settings.Secure.getString(getContentResolver(), Settings.Secure.ANDROID_ID);
        float batteryLevel = getBatteryLevel();

        // ساختن JSONObject برای ارسال
        JSONObject jsonBody = new JSONObject();
        try {
            jsonBody.put("latitude", lat);
            jsonBody.put("longitude", lon);
            jsonBody.put("android_id", androidId);
            jsonBody.put("battery_level", batteryLevel);
            jsonBody.put("speed", speed);
            jsonBody.put("device_model", deviceModel);
        } catch (JSONException e) {
            Log.e(TAG, "Error creating JSON: " + e.getMessage());
            return;
        }

        JsonObjectRequest request = new JsonObjectRequest(
                Request.Method.POST,
                SERVER_URL,
                jsonBody,
                response -> Log.d(TAG, "Server response: " + response.toString()),
                error -> Log.e(TAG, "Volley error: " + error.toString())
        ) {
            @Override
            public Map<String, String> getHeaders() {
                Map<String, String> headers = new HashMap<>();
                headers.put("Content-Type", "application/json");
                return headers;
            }
        };

        // تنظیم Timeout و Retry Policy
        request.setRetryPolicy(new DefaultRetryPolicy(
                10000, // Timeout 10 ثانیه
                DefaultRetryPolicy.DEFAULT_MAX_RETRIES,
                DefaultRetryPolicy.DEFAULT_BACKOFF_MULT));

        requestQueue.add(request);
    }

    private float getBatteryLevel() {
        BatteryManager bm = (BatteryManager) getSystemService(BATTERY_SERVICE);
        int level = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY);
        return level / 100f;
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == 100 && grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            startLocationUpdates();
        } else {
            Toast.makeText(this, "Location permission denied", Toast.LENGTH_SHORT).show();
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        mapview.onResume();
    }

    @Override
    protected void onPause() {
        super.onPause();
        mapview.onPause();
    }
}