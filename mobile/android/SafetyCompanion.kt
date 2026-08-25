package com.careconnect.safety

import android.Manifest
import android.app.*
import android.content.Context
import android.content.Intent
import android.hardware.*
import android.location.Location
import android.media.AudioAttributes
import android.media.MediaPlayer
import android.net.Uri
import android.os.*
import android.view.KeyEvent
import androidx.core.app.NotificationCompat
import androidx.work.*
import okhttp3.*
import org.json.JSONObject
import java.io.IOException
import java.util.UUID
import java.util.concurrent.TimeUnit
import kotlin.math.sqrt

/**
 * Additive native implementation for CareConnect Safety & Companion.
 *
 * API base must point at the same Django deployment:
 *   POST /api/safety-companion/silent-sos/
 *   POST /api/safety-companion/signals/
 *
 * The snippets assume the app already stores its JWT in SharedPreferences.
 */
object SafetyApi {
    private const val BASE = "https://YOUR-CARECONNECT-DOMAIN"
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    fun post(context: Context, path: String, body: JSONObject) {
        val token = context.getSharedPreferences("careconnect", Context.MODE_PRIVATE)
            .getString("access_token", "") ?: return
        val request = Request.Builder()
            .url("$BASE/api/safety-companion/$path")
            .addHeader("Authorization", "Bearer $token")
            .post(body.toString().toRequestBody("application/json".toMediaType()))
            .build()
        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {}
            override fun onResponse(call: Call, response: Response) { response.close() }
        })
    }
}

object LocationOnce {
    // Replace with your existing FusedLocationProviderClient wrapper.
    fun lastKnown(context: Context, done: (Location?) -> Unit) {
        // In the real app, call FusedLocationProviderClient.lastLocation here.
        // The feature must request ACCESS_FINE_LOCATION first.
        done(null)
    }
}

/** 1. SILENT TRIPLE PRESS — foreground/in-app implementation. */
class SafetyKeyActivity : Activity() {
    private val presses = ArrayDeque<Long>()
    private val windowMs = 900L

    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        if (keyCode != KeyEvent.KEYCODE_VOLUME_DOWN || event?.repeatCount != 0) {
            return super.onKeyDown(keyCode, event)
        }
        val now = SystemClock.elapsedRealtime()
        while (presses.isNotEmpty() && now - presses.first() > windowMs) presses.removeFirst()
        presses.addLast(now)
        if (presses.size >= 3) {
            presses.clear()
            // No Toast, notification, dialog, sound or UI update.
            LocationOnce.lastKnown(this) { loc ->
                val json = JSONObject()
                    .put("latitude", loc?.latitude)
                    .put("longitude", loc?.longitude)
                    .put("trigger_id", UUID.randomUUID().toString())
                    .put("client_timestamp", java.time.Instant.now().toString())
                    .put("source", "android_volume_down_triple_press")
                SafetyApi.post(this, "silent-sos/", json)
            }
        }
        // Consume the volume event so Android does not change volume for this trigger.
        return true
    }
}

/**
 * Optional background trigger.
 * Android requires the user to explicitly enable this accessibility service.
 * Do not enable it programmatically.
 */
class SafetyCompanionKeyService : android.accessibilityservice.AccessibilityService() {
    private val presses = ArrayDeque<Long>()
    private val windowMs = 900L

    override fun onServiceConnected() {
        serviceInfo = serviceInfo.apply {
            flags = flags or android.accessibilityservice.AccessibilityServiceInfo.FLAG_REQUEST_FILTER_KEY_EVENTS
        }
    }

    override fun onKeyEvent(event: KeyEvent): Boolean {
        if (event.action != KeyEvent.ACTION_DOWN ||
            event.repeatCount != 0 ||
            event.keyCode != KeyEvent.KEYCODE_VOLUME_DOWN) return false

        val now = SystemClock.elapsedRealtime()
        while (presses.isNotEmpty() && now - presses.first() > windowMs) presses.removeFirst()
        presses.addLast(now)
        if (presses.size >= 3) {
            presses.clear()
            LocationOnce.lastKnown(this) { loc ->
                SafetyApi.post(this, "silent-sos/", JSONObject()
                    .put("latitude", loc?.latitude)
                    .put("longitude", loc?.longitude)
                    .put("trigger_id", UUID.randomUUID().toString())
                    .put("source", "android_accessibility_volume_down_triple_press"))
            }
        }
        return true
    }

    override fun onAccessibilityEvent(event: android.view.accessibility.AccessibilityEvent?) {}
    override fun onInterrupt() {}
}

/** 2. FAKE CALL — local-only decoy activity. */
class FakeCallActivity : Activity() {
    private var player: MediaPlayer? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_fake_call)

        // activity_fake_call.xml should contain:
        // callerName, acceptButton, declineButton.
        val ringtone = android.provider.Settings.System.DEFAULT_RINGTONE_URI
        player = MediaPlayer.create(this, ringtone)
        player?.isLooping = true
        player?.setAudioAttributes(
            AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_NOTIFICATION_RINGTONE)
                .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                .build()
        )
        player?.start()

        findViewById<android.view.View>(R.id.declineButton).setOnClickListener { finish() }
        findViewById<android.view.View>(R.id.acceptButton).setOnClickListener {
            player?.stop()
            findViewById<android.widget.TextView>(R.id.callStatus).text = "Connected"
            findViewById<android.view.View>(R.id.acceptButton).visibility = android.view.View.GONE
        }
    }

    override fun onDestroy() {
        player?.release()
        player = null
        super.onDestroy()
    }
}

/** 3 + 4. FALL AND INACTIVITY SENSOR. */
class SafetyMotionEngine(private val context: Context) : SensorEventListener {
    private val sm = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val accel = sm.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
    private var lowGAt = 0L
    private var impactAt = 0L
    private var lastMotionAt = SystemClock.elapsedRealtime()
    private var impactMagnitude = 0.0

    fun start() {
        accel?.let { sm.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME) }
        lastMotionAt = SystemClock.elapsedRealtime()
    }

    fun stop() = sm.unregisterListener(this)

    override fun onSensorChanged(e: SensorEvent) {
        val g = sqrt(
            (e.values[0] * e.values[0]) +
            (e.values[1] * e.values[1]) +
            (e.values[2] * e.values[2])
        ) / SensorManager.GRAVITY_EARTH

        if (kotlin.math.abs(g - 1.0) > 0.12) lastMotionAt = SystemClock.elapsedRealtime()

        val now = SystemClock.elapsedRealtime()
        if (g < 0.60) lowGAt = now

        // Candidate impact within 1.2 s of unloading.
        if (lowGAt > 0 && now - lowGAt < 1200 && g > 2.50) {
            impactAt = now
            impactMagnitude = g
            lowGAt = 0
        }

        // Confirm post-impact stillness before sending.
        if (impactAt > 0 && now - impactAt in 8000L..15000L) {
            val quiet = g in 0.88..1.12
            if (quiet) {
                sendSignal("fall", 0.90, mapOf(
                    "impact_g" to impactMagnitude,
                    "post_fall_stillness_seconds" to (now - impactAt) / 1000
                ))
                impactAt = 0
            }
        }

        // Inactivity is evaluated every event; WorkManager can provide the
        // periodic background check when the sensor stream is not active.
        val inactivityMinutes = 60L
        if ((now - lastMotionAt) >= inactivityMinutes * 60_000L) {
            sendSignal("inactivity", 0.90, mapOf("inactive_minutes" to inactivityMinutes))
            lastMotionAt = now
        }
    }

    private fun sendSignal(type: String, confidence: Double, metadata: Map<String, Any>) {
        val json = JSONObject().put("signal_type", type).put("confidence", confidence)
        val meta = JSONObject()
        metadata.forEach { (k, v) -> meta.put(k, v) }
        json.put("metadata", meta)
        LocationOnce.lastKnown(context) { loc ->
            json.put("latitude", loc?.latitude).put("longitude", loc?.longitude)
            SafetyApi.post(context, "signals/", json)
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
}

/** Background inactivity check. */
class InactivityWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {
    override suspend fun doWork(): Result {
        // Persist last-motion timestamp in SharedPreferences from SafetyMotionEngine.
        val prefs = applicationContext.getSharedPreferences("careconnect_safety", Context.MODE_PRIVATE)
        val last = prefs.getLong("last_motion_at", System.currentTimeMillis())
        val threshold = prefs.getLong("inactivity_minutes", 60) * 60_000L
        if (System.currentTimeMillis() - last >= threshold) {
            SafetyApi.post(applicationContext, "signals/", JSONObject()
                .put("signal_type", "inactivity")
                .put("confidence", 0.90)
                .put("metadata", JSONObject().put("inactive_ms", System.currentTimeMillis() - last)))
            prefs.edit().putLong("last_motion_at", System.currentTimeMillis()).apply()
        }
        return Result.success()
    }
}

/**
 * 5. TFLite distress classifier.
 *
 * Put a real, trained model at app/src/main/assets/distress_detector.tflite.
 * The model should expose a float distress probability for a short audio window.
 * Audio never leaves the phone while the model is running.
 *
 * Keep the model contract documented with the ML team (sample rate, window,
 * tensor shape and labels). The backend deliberately accepts only the final
 * probability/event, never a continuous microphone stream.
 */
class DistressDetector(private val context: Context) {
    private var lastTrigger = 0L

    fun onModelProbability(probability: Float) {
        // Debounce to prevent a single scream from generating multiple incidents.
        val now = SystemClock.elapsedRealtime()
        if (probability < 0.75f || now - lastTrigger < 30_000) return
        lastTrigger = now
        SafetyApi.post(context, "signals/", JSONObject()
            .put("signal_type", "voice_distress")
            .put("confidence", probability)
            .put("metadata", JSONObject()
                .put("model", "distress_detector_v1")
                .put("window_ms", 2000)))
    }
}

/** 6. Daily wellness local prompt. Server still enforces the deadline. */
fun scheduleDailyWellnessPrompt(context: Context) {
    val request = PeriodicWorkRequestBuilder<WellnessPromptWorker>(24, TimeUnit.HOURS)
        .build()
    WorkManager.getInstance(context).enqueueUniquePeriodicWork(
        "careconnect_daily_wellness",
        ExistingPeriodicWorkPolicy.UPDATE,
        request
    )
}

class WellnessPromptWorker(ctx: Context, params: WorkerParameters) : Worker(ctx, params) {
    override fun doWork(): Result {
        // Show a local notification. The user can press "I'm OK" which calls
        // POST /api/safety-companion/wellness/<id>/action/ with {"action":"safe"}.
        val nm = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channel = NotificationChannel("wellness", "Daily wellness", NotificationManager.IMPORTANCE_DEFAULT)
        nm.createNotificationChannel(channel)
        nm.notify(
            7811,
            NotificationCompat.Builder(applicationContext, "wellness")
                .setSmallIcon(R.drawable.ic_notification)
                .setContentTitle("CareConnect wellness check")
                .setContentText("Are you okay? Tap to confirm your safety.")
                .setAutoCancel(true)
                .build()
        )
        return Result.success()
    }
}
