import socket
for port in [6379, 3005, 3000]:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        result = s.connect_ex(('localhost', port))
        print(f"Port {port}: {'Open' if result == 0 else 'Closed'}")
