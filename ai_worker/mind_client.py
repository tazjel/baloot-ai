
import torch
import logging
from pathlib import Path
from ai_worker.learning.mind_reader import MindReaderNet
from ai_worker.learning.mind_utils import MindVocab
import os

logger = logging.getLogger(__name__)

class MindClient:
    _instance = None
    
    def __init__(self, model_path=None):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Load Model
        self.model = MindReaderNet().to(self.device)
        
        if model_path is None:
            # Default location
            base = Path(__file__).parent
            model_path = base / "models" / "mind_reader_v1.pth"
            
        try:
            if os.path.exists(model_path):
                self.model.load_state_dict(torch.load(model_path, map_location=self.device))
                self.model.eval()
                self.active = True
                logger.info(f"MindReader loaded from {model_path} on {self.device}")
            else:
                logger.warning(f"MindReader model not found at {model_path}. Inference disabled.")
                self.active = False
        except Exception as e:
            logger.error(f"Failed to load MindReader: {e}")
            self.active = False
            
    def _vectorize_history(self, game_state, perspective_idx=0):
        """
        Convert LIVE game state to tensor sequence.
        Reconstructs sequence from:
        1. Bidding (game_state['bid'])
        2. Completed Tricks (game_state['tricks'])
        3. Current Trick (game_state['tableCards'])
        """
        tokens = [MindVocab.START]
        
        # 1. Bidding
        # In live state, we might only have the winning bid info easily accessible
        # Ideally we want full bidding history. 
        # If 'bids' list exists in state, use it. Else use winning bid as proxy.
        bid_info = game_state.get('bid', {})
        if bid_info:
            bid_type = bid_info.get('type', 'PASS')
            if bid_type:
                t = MindVocab.get_bid_token(bid_type)
                if t: tokens.append(t)
                
        # 2. Completed Tricks
        tricks = game_state.get('tricks', [])
        for trick in tricks:
            # Trick is dict: {cards: [..], playedBy: [..], winner: ..}
            # We need to interleave them correctly.
            # Assuming 'cards' and 'playedBy' are aligned lists.
            t_cards = trick.get('cards', [])
            # t_players = trick.get('playedBy', []) # Names or Indices?
            # In live state playedBy is usually list of names/indices.
            # For Tokenization, we just need the CARD token. Player ID is implicit in turn order?
            # Actually MindVocab only encodes Card/Bid. It doesn't encode Player ID.
            # So just sequence of cards is enough for V1.
            
            for c_obj in t_cards:
                 # c_obj might be dict or Card object
                 if isinstance(c_obj, dict):
                     c_str = self._card_to_str(c_obj)
                 else:
                     c_str = f"{c_obj.suit}{c_obj.rank}"
                     
                 t = MindVocab.get_card_token(c_str)
                 if t: tokens.append(t)
                 
        # 3. Current Trick (Table Cards)
        table = game_state.get('tableCards', [])
        for tc in table:
             c_obj = tc.get('card')
             if isinstance(c_obj, dict):
                 c_str = self._card_to_str(c_obj)
             else:
                 c_str = f"{c_obj.suit}{c_obj.rank}"

             t = MindVocab.get_card_token(c_str)
             if t: tokens.append(t)
                
        return torch.tensor(tokens, dtype=torch.long).unsqueeze(0).to(self.device)

    def _card_to_str(self, c_dict):
        # Helper to convert {'suit': 'H', 'rank': 'A'} to 'HA'
        # Suit might be symbol or letter.
        s = c_dict.get('suit', '')
        r = c_dict.get('rank', '')
        # Normalize suit symbols
        suit_map = {'♥': 'H', '♦': 'D', '♠': 'S', '♣': 'C'}
        s_char = suit_map.get(s, s) # Default to itself if already 'H'
        return f"{s_char}{r}"

    def infer_hands(self, game_history):
        """
        Returns probability distribution of hidden cards.
        Output: { player_id (0-3): { card_idx (0-31): probability } }
        """
        if not self.active: return None
        
        try:
            # Prepare Input
            x = self._vectorize_history(game_history, 0) # Perspective 0 for now
            
            with torch.no_grad():
                # pred_l (Left), pred_p (Partner), pred_r (Right) relative to Perspective 0
                # Our Model outputs: [Batch, 32] logits
                # output is (out_left, out_partner, out_right) - Tuple of tensors
                # Wait, training collate masked it?
                # Actually model returns: out_left, out_partner, out_right
                
                out_l, out_p, out_r = self.model(x)
                
                # Sigmoid for probabilities
                prob_l = torch.sigmoid(out_l).squeeze(0).cpu().numpy()
                prob_p = torch.sigmoid(out_p).squeeze(0).cpu().numpy()
                prob_r = torch.sigmoid(out_r).squeeze(0).cpu().numpy()
                
                # Map to Absolute Players (assuming P0 is viewpoint)
                # Right = 1, Partner = 2, Left = 3
                return {
                    1: prob_r,
                    2: prob_p,
                    3: prob_l
                }
                
        except Exception as e:
            logger.error(f"MindReader Inference Error: {e}")
            return None

    def get_heatmap(self, game_history):
        """
        Returns user-friendly heatmap for visualization.
        """
        probs = self.infer_hands(game_history)
        if not probs: return {}
        
        # Convert to dictionary keyed by player index -> list of card probabilities
        # UI expects specific format? Let's just return raw probabilities for now.
        return {
            "right": probs[1].tolist(),
            "partner": probs[2].tolist(),
            "left": probs[3].tolist()
        }

# Singleton
mind_client = MindClient()
