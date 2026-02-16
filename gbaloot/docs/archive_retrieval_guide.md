# Archive Retrieval Setup Guide

> **Goal**: Capture the API traffic from the Source mobile app's "Archives" feature, so we can retrieve hundreds of complete game replays for benchmarking our engine.

---

## What You Need

| Item | Details |
|------|---------|
| Your PC (Windows) | Already set up with Python |
| Your Android phone | With the Source app installed + game archives |
| Same WiFi network | Both devices on the same network |

---

## Step 1: Install mitmproxy on Your PC

Open PowerShell and run:

```powershell
pip install mitmproxy
```

Verify it works:

```powershell
mitmdump --version
```

You should see something like `Mitmproxy: 11.x.x`.

---

## Step 2: Find Your PC's Local IP Address

In PowerShell:

```powershell
ipconfig
```

Look for your WiFi adapter's **IPv4 Address**, something like `192.168.1.105`.

Write this down — you'll need it for the phone setup.

---

## Step 3: Start mitmproxy in Capture Mode

Open PowerShell and run:

```powershell
mitmdump --mode regular --save-stream-filter "~d kammelna" -w gbaloot_archive_capture.flow --set flow_detail=3
```

**What this command does:**
- `--mode regular` — runs as a standard HTTP/HTTPS proxy
- `--save-stream-filter "~d kammelna"` — only saves traffic to/from the source domain
- `-w gbaloot_archive_capture.flow` — saves to this file
- `--set flow_detail=3` — shows full request/response details in the terminal

**Leave this running** — it's now listening on port **8080**.

Alternatively, to save as HAR format (easier to read):

```powershell
mitmdump --mode regular -w gbaloot_archive_capture.flow --set flow_detail=3
```

> After you're done, you can convert to HAR with:
> ```powershell
> mitmdump -r gbaloot_archive_capture.flow --set hardump=gbaloot_archive.har
> ```

---

## Step 4: Configure Your Android Phone

### 4a. Set WiFi Proxy

1. Go to **Settings → WiFi**
2. Long-press your connected WiFi network → **Modify network** → **Advanced options**
3. Set **Proxy** to **Manual**
4. Enter:
   - **Proxy hostname**: Your PC's IP (e.g., `192.168.1.105`)
   - **Proxy port**: `8080`
5. Save

### 4b. Install the mitmproxy Certificate

This is required to intercept HTTPS traffic. Without it, you'll only see encrypted blobs.

1. On your phone's browser, go to: **http://mitm.it**
2. Tap **Android** to download the certificate
3. Go to **Settings → Security → Install from storage** (or search "Install certificates")
4. Find the downloaded `mitmproxy-ca-cert.pem` file and install it
5. Name it anything (e.g., "mitmproxy")

> **Android 7+**: You may need to move the cert to the system store. The easiest way:
> 1. Go to **Settings → Security → Trusted credentials → User** tab
> 2. Verify "mitmproxy" appears there
> 3. Some apps only trust system certs — if the source app shows errors, see the Troubleshooting section below

### 4c. Verify the Proxy Works

1. Open your phone's browser
2. Go to any website (e.g., `https://google.com`)
3. Check your PC terminal — you should see the request appear in the mitmproxy output
4. If it works, the proxy is correctly configured

---

## Step 5: Capture the Archive Traffic

Now the exciting part:

1. **Open the Source app** on your phone
2. **Go to Archives / History** (the section that shows your past games)
3. **Browse your games slowly** — scroll through the list, open a few game details
4. **Open at least 5-10 different games** and view their full replay/details
5. **Scroll through ALL pages** of your archive if possible

**Watch your PC terminal** — you should see HTTP requests flowing:

```
GET https://api.source.com/v1/games/history?page=1 → 200 OK
GET https://api.source.com/v1/games/12345/replay → 200 OK
...
```

The more games you browse, the more data we capture.

---

## Step 6: Stop and Save

1. On your PC, press **Ctrl+C** in the mitmproxy terminal to stop
2. The capture is saved to `gbaloot_archive_capture.flow`
3. **Remove the proxy** from your phone:
   - Go back to WiFi settings
   - Set Proxy back to **None**
4. Copy the capture file to the project:

```powershell
# Create the archive captures directory
mkdir -p c:\Users\MiEXCITE\Projects\baloot-ai\gbaloot\data\archive_captures

# Move the capture file  
Move-Item gbaloot_archive_capture.flow c:\Users\MiEXCITE\Projects\baloot-ai\gbaloot\data\archive_captures\
```

Also export as HAR for easier debugging:

```powershell
mitmdump -r c:\Users\MiEXCITE\Projects\baloot-ai\gbaloot\data\archive_captures\gbaloot_archive_capture.flow --set hardump=c:\Users\MiEXCITE\Projects\baloot-ai\gbaloot\data\archive_captures\gbaloot_archive.har
```

---

## Step 7: Hand Off to Claude/Gemini

Once you have the capture file, tell me (Gemini) or Claude:

> "I've captured the archive traffic. The file is at `gbaloot/data/archive_captures/gbaloot_archive_capture.flow`"

We will then:
1. **Analyze** the captured traffic to identify API endpoints
2. **Parse** the game data from the API responses
3. **Convert** each game into our benchmark format
4. **Run the benchmark** on your entire archive

---

## Troubleshooting

### "Certificate not trusted" or SSL errors in the Source app

Some Android apps use **certificate pinning** — they only trust specific certificates, not user-installed ones. Solutions:

1. **Try HTTP Toolkit** instead — it has a one-click Android setup that handles cert pinning:
   ```
   https://httptoolkit.com/
   ```
   Download the desktop app + the Android companion app from Play Store.

2. **Use Frida** to bypass cert pinning (advanced):
   - Requires a rooted phone or an emulator
   - Script: `frida -U -f com.kammelna.baloot -l bypass_pinning.js`

3. **Use an Android emulator** (BlueStacks, LDPlayer, or Android Studio emulator):
   - Install the Source app on the emulator
   - Emulators are easier to configure with custom certificates
   - Log into your account on the emulator

### "No traffic showing in mitmproxy"

1. Verify your phone and PC are on the **same WiFi network**
2. Check the proxy settings: hostname = your PC's IP, port = 8080
3. Try accessing `http://mitm.it` on your phone — if it doesn't load, the proxy isn't configured
4. Check if Windows Firewall is blocking port 8080:
   ```powershell
   netsh advfirewall firewall add rule name="mitmproxy" dir=in action=allow protocol=TCP localport=8080
   ```

### "I can't see game details in the traffic"

The app might fetch game data differently than expected:
- Some apps use **WebSocket** for real-time data even in the archive viewer
- Some apps **cache** game data locally and don't make network calls for previously viewed games
- Try: clear the app cache before capturing, then browse archives fresh

### "I can't install the certificate on my phone"

For Android 11+:
1. Go to **Settings → Security → Encryption & credentials → Install a certificate → CA certificate**
2. Acknowledge the security warning
3. Select the downloaded `.pem` file

For Android 14+:
1. The process may require developer mode enabled
2. **Settings → Developer options → Wireless debugging** can help

---

## Alternative Approach: Android Emulator (Easier)

If configuring your physical phone is difficult, use an emulator:

### Using BlueStacks (Recommended for simplicity)

```powershell
# 1. Download BlueStacks from https://www.bluestacks.com/
# 2. Install and launch BlueStacks
# 3. Install the Source app from Play Store in BlueStacks
# 4. Log into your account
# 5. Configure BlueStacks proxy:
#    Settings → Network → Set proxy to 192.168.1.105:8080
# 6. Install mitmproxy certificate in BlueStacks
# 7. Browse your archives
```

### Using Android Studio Emulator (Most flexible)

```powershell
# 1. Create an AVD (Android Virtual Device) without Google Play Services
#    (non-Google images allow writable /system for cert install)
# 2. Start emulator with proxy:
emulator -avd Pixel_7_API_34 -http-proxy 192.168.1.105:8080
# 3. Install cert on the emulator
# 4. Install Source APK via adb:
adb install kammelna.apk
# 5. Log in and browse archives
```

---

## What Happens Next

After capture, the workflow is:

```
You (capture) → capture file (.flow/.har)
                  ↓
Claude (parse) → detect API endpoints
                  ↓
Claude (code)  → archive_retriever.py
                  ↓
                 Parse all games → ArchivedGame objects
                  ↓
                 Convert to ProcessedSession format
                  ↓
                 Feed into GameComparator
                  ↓
                 📊 Benchmark scorecard with HUNDREDS of games
```

This will take our benchmark from 95 tricks to potentially **thousands** — making it statistically bulletproof.
