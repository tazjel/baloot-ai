
import os
import sys
import torch
import torch.onnx
import rlcard
from rlcard.agents import NFSPAgent
from ai_training.baloot_env import BalootEnv

# Ensure env can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def export_onnx():
    log_dir = 'ai_training/experiments/baloot_nfsp_result/'
    onnx_path = 'ai_training/baloot_brain.onnx'
    
    # Initialize env to get shapes
    env = BalootEnv(config={'allow_step_back': False, 'seed': 42})
    
    # Re-initialize agent to load weights
    device = torch.device('cpu') # Export on CPU
    agent = NFSPAgent(
        num_actions=env.action_num,
        state_shape=env.state_shape,
        hidden_layers_sizes=[128, 128],
        q_mlp_layers=[128, 128],
        device=device
    )
    
    # Load checkpoint
    checkpoint_path = os.path.join(log_dir, 'checkpoint_nfsp.pt')
    if not os.path.exists(checkpoint_path):
        print(f"Error: Checkpoint not found at {checkpoint_path}")
        return

    # Load state dict via agent helper
    # agent.load(log_dir) -> Doesn't exist. Manually load.
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    
    # Debug structure
    # print(f"Agent dir: {dir(agent)}")
    
    # Keys in checkpoint: ['policy_network', 'rl_agent', ...]
    # It seems 'policy_network' key holds the state dict for the SL policy.
    
    # Find where to load it.
    # Check if agent has policy_network
    if hasattr(agent, 'policy_network'):
        model = agent.policy_network
    elif hasattr(agent, '_policy_estimator') and hasattr(agent._policy_estimator, 'policy_network'):
        model = agent._policy_estimator.policy_network
    else:
        # Fallback inspection
        print(f"Agent attributes: {agent.__dict__.keys()}")
        return

    if 'policy_network' in checkpoint:
         pn_state = checkpoint['policy_network']
         if 'mlp' in pn_state and isinstance(pn_state['mlp'], dict):
             # Detected nested structure
             try:
                 model.mlp.load_state_dict(pn_state['mlp'])
             except Exception as e:
                 print(f"Failed to load mlp: {e}")
                 # Fallback: model might expect flattened keys? 
                 # But model.mlp expects keys like '0.weight'.
         else:
             model.load_state_dict(pn_state)
    else:
         print("State dict for policy_network not found in checkpoint")

    model.eval()
    
    # Dummy Input
    # State shape is [102]
    dummy_input = torch.randn(1, 102, requires_grad=True).to(device)
    
    # Export
    torch.onnx.export(
        model,
        dummy_input,
        onnx_path,
        export_params=True,
        opset_version=11,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
    )
    
    print(f"Model exported to {onnx_path}")
    
    # Verify logic (requires onnx package)
    try:
        import onnx
        onnx_model = onnx.load(onnx_path)
        onnx.checker.check_model(onnx_model)
        print("ONNX model is valid.")
    except ImportError:
        print("ONNX package not installed, skipping validation.")

if __name__ == '__main__':
    export_onnx()
