
import sys
import os
import numpy as np

# Ensure we can import the env
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_training.baloot_env import BalootEnv

def test_random_play():
    env = BalootEnv(config={'allow_step_back': False})
    state, player_id = env.reset()
    
    print(f"Initial State Shape: {state['obs'].shape}")
    print(f"Initial Legal Actions: {state['legal_actions']}")
    
    done = False
    step_count = 0
    
    try:
        while not env.is_over() and step_count < 1000:
            legal_actions = state['legal_actions']
            if not legal_actions:
                print("No legal actions but game not over?")
                break
                
            action = np.random.choice(list(legal_actions.keys()))
            # print(f"Step {step_count}: Player {player_id} plays Action {action}")
            
            state, player_id = env.step(action)
            step_count += 1
            
        if env.is_over():
             print("Game Over reached!")
             payoffs = env.get_payoff()
             print(f"Payoffs: {payoffs}")


    except Exception as e:
        print(f"CRASHED at step {step_count}: {e}")
        import traceback
        traceback.print_exc()
        raise e
        
    print(f"Successfully ran {step_count} steps without crash.")

if __name__ == "__main__":
    test_random_play()
