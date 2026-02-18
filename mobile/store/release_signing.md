# Release Signing & Build Guide

## Android

### Step 1: Create Release Keystore

```powershell
keytool -genkey -v -keystore baloot-ai-release.keystore -alias baloot-ai -keyalg RSA -keysize 2048 -validity 10000
```

You will be prompted for:
- Keystore password (use a strong password, save it securely)
- Key password (can be same as keystore password)
- Name, organization, location fields

> [!CAUTION]
> **Never commit the keystore file or passwords to git.** Store the keystore in a secure location outside the repo. If you lose the keystore, you cannot update the app on Google Play.

### Step 2: Create `key.properties`

Create `mobile/android/key.properties` (this file is gitignored):

```properties
storePassword=YOUR_KEYSTORE_PASSWORD
keyPassword=YOUR_KEY_PASSWORD
keyAlias=baloot-ai
storeFile=C:/path/to/baloot-ai-release.keystore
```

### Step 3: Update `build.gradle.kts`

In `mobile/android/app/build.gradle.kts`, add signing config:

```kotlin
// Add above android { block
val keystoreProperties = java.util.Properties()
val keystoreFile = rootProject.file("key.properties")
if (keystoreFile.exists()) {
    keystoreFile.inputStream().use { keystoreProperties.load(it) }
}

android {
    // ... existing config ...

    signingConfigs {
        create("release") {
            keyAlias = keystoreProperties["keyAlias"] as String?
            keyPassword = keystoreProperties["keyPassword"] as String?
            storeFile = keystoreProperties["storeFile"]?.let { file(it) }
            storePassword = keystoreProperties["storePassword"] as String?
        }
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")
            // existing minify/proguard config stays
        }
    }
}
```

### Step 4: Build Release APK

```powershell
cd "C:/Users/MiEXCITE/Projects/baloot-ai/mobile"
C:/Users/MiEXCITE/development/flutter/bin/flutter.bat build apk --release
```

Output: `build/app/outputs/flutter-apk/app-release.apk`

### Step 5: Build App Bundle (for Google Play)

```powershell
C:/Users/MiEXCITE/development/flutter/bin/flutter.bat build appbundle --release
```

Output: `build/app/outputs/bundle/release/app-release.aab`

> [!TIP]
> Google Play requires `.aab` (app bundle) format. APKs are for direct distribution only.

---

## iOS

### Step 1: Apple Developer Account
- Requires [Apple Developer Program](https://developer.apple.com/programs/) membership ($99/year)
- Register a Bundle ID: `com.tazjel.balootai`

### Step 2: Xcode Signing
1. Open `mobile/ios/Runner.xcworkspace` in Xcode
2. Select the **Runner** target → **Signing & Capabilities**
3. Set Team to your Apple Developer account
4. Set Bundle Identifier to `com.tazjel.balootai`
5. Enable "Automatically manage signing"

### Step 3: Build Archive
```bash
cd mobile
flutter build ios --release
```

Then in Xcode:
1. **Product → Archive**
2. In Organizer → **Distribute App**
3. Choose **App Store Connect**
4. Upload

### Step 4: App Store Connect
1. Go to [App Store Connect](https://appstoreconnect.apple.com)
2. Create a new app with the Bundle ID
3. Fill in app metadata (use content from `listing_ar.md`)
4. Upload screenshots
5. Submit for review

---

## Pre-Release Checklist

- [ ] `flutter analyze` — 0 errors
- [ ] `flutter test` — all pass
- [ ] App icon is custom (not default Flutter)
- [ ] App name shows "بلوت AI"
- [ ] Privacy policy URL is live
- [ ] Screenshots captured for store listing
- [ ] Version number updated in `pubspec.yaml`
- [ ] `flutter build apk --release` succeeds
- [ ] `flutter build appbundle --release` succeeds
