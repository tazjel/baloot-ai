import socket
import time
import sys

def check_port(port, name):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            result = s.connect_ex(('localhost', port))
            if result == 0:
                print(f"✅ {name} is ALIVE on port {port}")
                return True
            else:
                print(f"❌ {name} is DOWN on port {port}")
                return False
    except Exception as e:
        print(f"❌ {name} Error: {e}")
        return False

print("Verifying Game Stack...")
time.sleep(2) 
backend = check_port(3005, "Backend")
frontend = check_port(5173, "Frontend")
redis = check_port(6379, "Redis")

if backend and frontend and redis:
    print("🚀 ALL SYSTEMS GO!")
    sys.exit(0)
else:
    print("⚠️  SYSTEM Check FAILED")
    sys.exit(1)
