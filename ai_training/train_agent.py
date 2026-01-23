
import os
import sys
import torch
import rlcard
from rlcard.agents import NFSPAgent
from rlcard.utils import tournament, reorganize, Logger

# Ensure env can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai_training.baloot_env import BalootEnv

def train(epochs=1000):
    # Make environment
    env = BalootEnv(config={'allow_step_back': False, 'seed': 42})
    
    # Set the iterations per episode check
    eval_env = BalootEnv(config={'allow_step_back': False, 'seed': 42})
    
    # Device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # Initialize Agent (NFSP)
    # Baloot has 4 players. We can train one agent and copy it? Or share memory?
    # Usually in RLCard for symmetric games, we train one agent playing against itself.
    # But Baloot is team based.
    # Detailed approach: Train one agent model that plays for ALL positions (Self-Play).
    
    agent = NFSPAgent(
        num_actions=env.action_num,
        state_shape=env.state_shape,
        hidden_layers_sizes=[128, 128], # Deep Network
        q_mlp_layers=[128, 128],
        device=device
    )
    
    # All players share the same agent (Self-Play)
    env.set_agents([agent for _ in range(env.num_players)])
    eval_env.set_agents([agent for _ in range(env.num_players)])
    
    # Paths
    log_dir = 'ai_training/experiments/baloot_nfsp_result/'
    model_path = os.path.join(log_dir, 'model.pth')
    os.makedirs(log_dir, exist_ok=True)
    
    with Logger(log_dir) as logger:
        for episode in range(epochs):
            # Generate data from one episode
            trajectories, payoffs = env.run(is_training=True)
            
            # Reorganize data and feed to agent
            trajectories = reorganize(trajectories, payoffs)
            
            for ts in trajectories[0]: # P0's trajectory (shared agent learns from all?)
                # NFSP usually expects us to feed all agent experiences if shared?
                # RLCard env.run returns trajectories for all players.
                # Since we share the agent object, we should feed it all experiences?
                # Actually, `env.run` changes turn.
                # If we passed `[agent, agent, ...]` they are indeed the SAME object.
                # So feeding `agent.feed` once per step in `env.run`?
                # No, `env.run` collects trajectories. We must manually feed.
                pass

            # Feed transitions to agent
            for t in trajectories:
                for ts in t:
                    agent.feed(ts)
                    
            # Evaluate
            if episode % 100 == 0:
                # Run tournament against random? Or just check payoff?
                # logger.log_performance(env.timestep, tournament(eval_env, 10)[0])
                print(f"Episode {episode} completed.")
                
            # Save
            if episode % 1000 == 0:
                agent.save_checkpoint(log_dir)
                
    # Final Save
    agent.save_checkpoint(log_dir)
    print(f"Model saved to {log_dir}")

if __name__ == '__main__':
    train(epochs=100) # Short run for verification
