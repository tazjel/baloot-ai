# Release Signing & Build Guide

## Android Release Build

### Step 1: Create Release Keystore
```bash
keytool -genkey -v \
  -keystore android/app/baloot-ai-release.keystore \
  -alias baloot-ai \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000
```

### Step 2: Create key.properties
Create `android/key.properties` (DO NOT commit this file):
```properties
storePassword=YOUR_STORE_PASSWORD
keyPassword=YOUR_KEY_PASSWORD
keyAlias=baloot-ai
storeFile=baloot-ai-release.keystore
```

### Step 3: Update build.gradle.kts
Replace the debug signing config in `android/app/build.gradle.kts`:
```kotlin
// Load keystore properties
val keystoreProperties = java.util.Properties()
val keystorePropertiesFile = rootProject.file("key.properties")
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(java.io.FileInputStream(keystorePropertiesFile))
}

android {
    signingConfigs {
        create("release") {
            keyAlias = keystoreProperties["keyAlias"] as String
            keyPassword = keystoreProperties["keyPassword"] as String
            storeFile = file(keystoreProperties["storeFile"] as String)
            storePassword = keystoreProperties["storePassword"] as String
        }
    }
    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")
            // ... existing minify/proguard config ...
        }
    }
}
```

### Step 4: Build Release APK
```bash
cd mobile
flutter build apk --release --dart-define=API_URL=https://your-server.com
```

### Step 5: Build App Bundle (for Play Store)
```bash
flutter build appbundle --release --dart-define=API_URL=https://your-server.com
```

Output: `build/app/outputs/bundle/release/app-release.aab`

## iOS Release Build

### Step 1: Configure Signing in Xcode
1. Open `mobile/ios/Runner.xcworkspace` in Xcode
2. Select Runner target → Signing & Capabilities
3. Select your Team (Apple Developer account)
4. Set Bundle Identifier: `com.balootai.balootAi`

### Step 2: Archive
1. Select "Any iOS Device" as build target
2. Product → Archive
3. Distribute App → App Store Connect

### Step 3: Alternative CLI Build
```bash
cd mobile
flutter build ipa --release --dart-define=API_URL=https://your-server.com
```

## Security Notes
- NEVER commit `key.properties` or `.keystore` files to git
- Add to `.gitignore`: `key.properties`, `*.keystore`, `*.jks`
- Store keystore backup in a secure location
- Document passwords in a password manager
