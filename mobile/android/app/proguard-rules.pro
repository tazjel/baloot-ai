# Flutter-specific ProGuard rules for بلوت AI
# Applied during release builds to minimize APK size.

# Flutter wrapper
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.** { *; }
-keep class io.flutter.util.** { *; }
-keep class io.flutter.view.** { *; }
-keep class io.flutter.** { *; }
-keep class io.flutter.plugins.** { *; }

# Dart native code
-keep class io.flutter.embedding.** { *; }

# WebSocket / Socket.IO
-keep class io.socket.** { *; }
-dontwarn io.socket.**

# Audioplayers
-keep class xyz.luan.audioplayers.** { *; }

# SharedPreferences
-keep class io.flutter.plugins.sharedpreferences.** { *; }

# Google Fonts (HTTP requests)
-keep class com.google.** { *; }
-dontwarn com.google.**

# Keep annotations
-keepattributes *Annotation*
-keepattributes SourceFile,LineNumberTable

# Remove logging in release
-assumenosideeffects class android.util.Log {
    public static boolean isLoggable(java.lang.String, int);
    public static int v(...);
    public static int d(...);
    public static int i(...);
}
