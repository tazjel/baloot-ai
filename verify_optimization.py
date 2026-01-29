import sys
import os
import time

# Add CWD to path
sys.path.append(os.getcwd())

def test_redis_persistence():
    print("Testing Redis Persistence...")
    try:
        from server.common import redis_client
        from server.room_manager import room_manager, Game
        
        if not redis_client:
            print("ERROR: redis_client is None. Is Redis running?")
            return False
            
        # Create Dummy Game
        room_id = room_manager.create_room()
        print(f"Created Room: {room_id}")
        
        # Verify it exists in Redis
        # (room_manager.create_room calls save_game which writes to Redis)
        
        # Manually check Redis
        if redis_client.exists(f"game:{room_id}"):
            print("SUCCESS: Game key found in Redis.")
        else:
            print("ERROR: Game key NOT found in Redis.")
            return False
            
        # Fetch back via Manager
        game = room_manager.get_game(room_id)
        if game and game.room_id == room_id:
             print("SUCCESS: Game retrieved correctly from Redis (Pickle works).")
        else:
             print("ERROR: Failed to retrieve game.")
             return False
             
        return True
        
    except ImportError as e:
        print(f"Import Error: {e}")
        return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_auth_utils():
    print("\nTesting Auth Utils...")
    try:
        import server.auth_utils as auth_utils
        
        token = auth_utils.generate_token("123", "test@example.com", "Test", "User")
        print(f"Generated Token: {token[:15]}...")
        
        payload = auth_utils.verify_token(token)
        if payload and payload['user_id'] == "123":
            print("SUCCESS: Token verified correctly.")
        else:
            print("ERROR: Token verification failed.")
            return False
            
        return True
    except Exception as e:
        print(f"Exception: {e}")
        return False

if __name__ == "__main__":
    r1 = test_redis_persistence()
    r2 = test_auth_utils()
    
    if r1 and r2:
        print("\nALL SYSTEM CHECKS PASSED.")
    else:
        print("\nSYSTEM CHECKS FAILED.")
