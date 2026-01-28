
import logging
import random
import torch
import os
from ai_worker.bot_context import BotContext
from ai_worker.learning.model import StrategyNet
from ai_worker.learning.feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)

class NeuralStrategy:
    def __init__(self, model_path=None):
        self.extractor = FeatureExtractor()
        self.model = StrategyNet()
        self.device = torch.device("cpu") # Inference on CPU is fine/safer for now
        self.model.to(self.device)
        self.model.eval()
        self.enabled = False
        
        # Load Model if exists
        if model_path and os.path.exists(model_path):
            try:
                self.model.load(model_path)
                self.enabled = True
                logger.info(f"Neural Strategy Loaded: {model_path}")
            except Exception as e:
                logger.error(f"Failed to load Neural Model: {e}")
                self.enabled = False
        else:
             logger.warning(f"Neural Model not found at {model_path}. Strategy Disabled.")

    def get_decision(self, ctx: BotContext) -> dict:
        if not self.enabled:
             return None
             
        try:
            # 1. Encode State
            # Pass legal moves mask? The net output is 32 cards.
            # We can mask output instead of input for now.
            vec = self.extractor.encode(ctx)
            tensor_in = torch.tensor(vec, dtype=torch.float32).unsqueeze(0).to(self.device)
            
            # 2. Inference
            with torch.no_grad():
                logits = self.model(tensor_in).squeeze(0) # [32]
                
            # 3. Mask Illegal Moves
            legal_indices = ctx.get_legal_moves()
            if not legal_indices:
                 return None
                 
            # Convert hand indices to Deck Indices (0-31)
            # The model predicts distinct cards 0-31.
            # We map: Model Output (0-31) -> Card Object -> Index in Hand
            
            # Create a simplified map: {DeckIndex: HandIndex}
            legal_map = {} # deck_idx -> hand_idx
            
            # Start with -Inf for all
            masked_logits = torch.full_like(logits, -1e9)
            
            for hand_idx in legal_indices:
                 card = ctx.hand[hand_idx]
                 deck_idx = self.extractor._get_card_index(card)
                 if deck_idx != -1:
                      masked_logits[deck_idx] = logits[deck_idx]
                      legal_map[deck_idx] = hand_idx
            
            # 4. Select Best
            best_deck_idx = torch.argmax(masked_logits).item()
            
            if best_deck_idx in legal_map:
                 best_hand_idx = legal_map[best_deck_idx]
                 
                 # Debug Score
                 score = logits[best_deck_idx].item()
                 
                 return {
                     "action": "PLAY",
                     "cardIndex": best_hand_idx,
                     "reasoning": f"Neural Network (Score: {score:.2f})"
                 }
            
            # Fallback (Should not happen unless empty mask)
            return None
            
        except Exception as e:
            logger.error(f"Neural Inference Failed: {e}")
            return None

    def predict_policy(self, ctx_or_game) -> dict:

        """
        Returns a dictionary mapping hand_index -> probability.
        Sum of probabilities will be 1.0 (Softmax).
        Calculates P(s, a) for PUCT MCTS.
        Supports both BotContext and FastGame.
        """
        if not self.enabled:
             # Fallback: Uniform distribution over legal moves
             legal = ctx_or_game.get_legal_moves()
             if not legal: return {}
             prob = 1.0 / len(legal)
             return {idx: prob for idx in legal}

        try:
            # 1. Encode
            is_fast = hasattr(ctx_or_game, 'played_cards_in_trick') # Duck type FastGame
            legal_indices = ctx_or_game.get_legal_moves()
            if not legal_indices: return {}

            if is_fast:
                 vec = self.extractor.encode_fast(ctx_or_game, legal_indices)
            else:
                 vec = self.extractor.encode(ctx_or_game, legal_indices)
                 
            tensor_in = torch.tensor(vec, dtype=torch.float32).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                logits = self.model(tensor_in).squeeze(0) # [32]

            # 2. Mask Illegal Moves (Indices)
            # Map Hand Indices to Deck Indices for Logit Lookup
            
            # Context Switch:
            # BotContext: self.hand[idx] -> Card Object
            # FastGame: self.hands[self.current_turn][idx] -> Card Object
            
            curr_hand = None
            if is_fast:
                 curr_hand = ctx_or_game.hands[ctx_or_game.current_turn]
            else:
                 curr_hand = ctx_or_game.hand
            
            masked_logits = []
            
            for hand_idx in legal_indices:
                 card = curr_hand[hand_idx]
                 deck_idx = self.extractor._get_card_index(card)
                 if deck_idx != -1:
                      masked_logits.append(logits[deck_idx])
                 else:
                      masked_logits.append(torch.tensor(-10.0))

            if not masked_logits: return {}

            # 3. Softmax
            masked_logits_tensor = torch.stack(masked_logits)
            probs = torch.nn.functional.softmax(masked_logits_tensor, dim=0)
            
            # 4. Build Result
            policy = {}
            for i, hand_idx in enumerate(legal_indices):
                 policy[hand_idx] = probs[i].item()
                 
            return policy

        except Exception as e:
            logger.error(f"Neural Policy Prediction Failed: {e}")
            # Fallback
            legal = ctx_or_game.get_legal_moves()
            if not legal: return {}
            return {idx: 1.0/len(legal) for idx in legal}
