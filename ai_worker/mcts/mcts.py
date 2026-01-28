
import math
import random
import time
from typing import Dict, List, Optional
from ai_worker.mcts.fast_game import FastGame

class MCTSNode:
    def __init__(self, move_idx: int, parent=None, prior: float = 0.0):
        self.move_idx = move_idx # The move that led to this node (Card Index in Hand)
        self.parent = parent
        self.children = {} # Map[move_idx] -> MCTSNode
        self.wins = 0.0
        self.visits = 0
        self.prior = prior # P(s, a) from Neural Net
        self.untried_moves = None # populate on first expansions

class MCTSSolver:
    def __init__(self, exploration_constant=1.414, neural_strategy=None):
        self.exploration_constant = exploration_constant # acts as C_puct in Hybrid Mode
        self.neural_strategy = neural_strategy

    def search(self, root_state: FastGame, timeout_ms: int = 100, max_iterations: int = None) -> int:
        """
        Runs MCTS for a specified valid time.
        Returns the best move index.
        """
        # Root Prior Calculation (if needed)
        # For root, we don't store prior on the node itself usually, but on its children.
        root_node = MCTSNode(move_idx=-1, prior=1.0)
        root_node.untried_moves = root_state.get_legal_moves()
        
        # Pre-expand root with priors if Neural Strategy exists
        if self.neural_strategy:
             # This ensures the very first selection uses policy
             self._expand_all_children(root_node, root_state)
        
        return self.search_with_details(root_state, timeout_ms, max_iterations, root_node)[0]

    def search_with_details(self, root_state: FastGame, timeout_ms: int = 100, max_iterations: int = None, root_node_override=None):
        """
        Runs MCTS and returns (best_move_idx, detailed_stats).
        stats: dict[move_idx] -> { 'visits': int, 'wins': float, 'win_rate': float }
        """
        if root_node_override:
             root_node = root_node_override
        else:
             root_node = MCTSNode(move_idx=-1)
             root_node.untried_moves = root_state.get_legal_moves()
        
        start_time = time.time()
        iterations = 0
        
        while (time.time() - start_time) * 1000 < timeout_ms:
            if max_iterations and iterations >= max_iterations:
                break
            iterations += 1
            node = root_node
            state = root_state.clone()
            
            # 1. Selection
            # Traverse until we hit a leaf or a node with untried moves
            # In PUCT, we usually expand fully at once or use priors.
            # Here keeping legacy structure: if untried_moves is not empty, we are at a frontier to expand.
            while not node.untried_moves and node.children:
                is_us_turn = (state.teams[state.current_turn] == 'us')
                node = self._select_child(node, is_us_turn)
                state.apply_move(node.move_idx)
                
            # 2. Expansion
            if node.untried_moves:
                # If using Neural Strategy, we might want to expand ALL children at once to attach priors
                # But to keep it similar to standard MCTS, we can expand one, 
                # OR we switch to "Expand All" for PUCT.
                # "Expand All" is better for PUCT because Selection needs priors of siblings.
                if self.neural_strategy:
                     node = self._expand_with_policy(node, state)
                else:
                     # Standard Random Expansion
                     move = random.choice(node.untried_moves)
                     state.apply_move(move)
                     node = self._expand(node, move, state)
                
            # 3. Simulation (Rollout)
            # Optimized rollout?
            # For now standard random
            steps = 0
            while not state.is_terminal():
                legal = state.get_legal_moves()
                if not legal: 
                    # Terminal but is_terminal returned false?
                    # This happens if round ends but FastGame logic didn't set is_finished?
                    # FastGame sets is_finished only when ALL hands empty.
                    break
                
                try:
                    move_idx = random.choice(legal)
                except Exception as e:
                    # Catch-all for any random.choice failure (IndexError, ValueError, etc)
                    # print(f"MCTS Choice Error: {e} | Legal: {legal}")
                    break
                    
                state.apply_move(move_idx)
                
            # 4. Backpropagation
            # Calculate reward from 'us' perspective
            us_score = state.scores['us']
            them_score = state.scores['them']
            
            score_diff = us_score - them_score
            reward = 0.5 + (score_diff / 100.0) 
            if reward > 1.0: reward = 1.0
            if reward < 0.0: reward = 0.0
            
            self._backpropagate(node, reward)
            
        if not root_node.children:
            # Fallback if no simulations ran (shouldn't happen with 100ms)
            legal = root_state.get_legal_moves()
            if not legal: return -1, {}
            return legal[0], {}

        # Select best move
        best_move = max(root_node.children.items(), key=lambda item: item[1].visits)[0]
        
        # Build details
        details = {}
        for move_idx, child in root_node.children.items():
            win_rate = child.wins / child.visits if child.visits > 0 else 0
            details[move_idx] = {
                'visits': child.visits,
                'wins': child.wins,
                'win_rate': win_rate,
                'prior': child.prior
            }
            
        return best_move, details

    def _select_child(self, node, is_us_turn: bool):
        # AlphaZero PUCT
        # PUCT = Q(s,a) + C * P(s,a) * sqrt(N_parent) / (1 + N_child)
        
        # If no neural strategy, fall back to UCB1 logic (where P(s,a) is implicitly uniform or ignored)
        
        best_score = float('-inf')
        best_child = None
        
        # Pre-calc sqrt(N_parent)
        sqrt_parent_visits = math.sqrt(node.visits)
        
        for child in node.children.values():
            if child.visits == 0:
                 q_value = 0.5 # Neutral prior for unvisited
                 if self.neural_strategy:
                      # Trust prior more for unvisited
                      # FPU (First Play Urgency) could be used here
                      pass
            else:
                 q_value = child.wins / child.visits
            
            if not is_us_turn:
                # Opponent wants to minimize 'us' score (maximize '1 - us')
                q_value = 1.0 - q_value
            
            # PUCT Term
            # If standard MCTS (no prior), node.prior is 0.0?? No, should handle legacy.
            # Legacy: UCB = Q + C * sqrt(ln N / n)
            
            if self.neural_strategy:
                 # PUCT
                 u_value = self.exploration_constant * child.prior * (sqrt_parent_visits / (1 + child.visits))
                 score = q_value + u_value
            else:
                 # Standard UCT
                 if child.visits == 0:
                      score = float('inf') # Ensure unvisited are visited
                 else:
                      exploit = q_value
                      explore = self.exploration_constant * math.sqrt(2 * math.log(node.visits) / child.visits)
                      score = exploit + explore
            
            if score > best_score:
                best_score = score
                best_child = child
                
        return best_child

    def _expand(self, node, move_idx, state):
        # Legacy Expansion (One at a time)
        child = MCTSNode(move_idx=move_idx, parent=node)
        child.untried_moves = state.get_legal_moves()
        node.untried_moves.remove(move_idx)
        node.children[move_idx] = child
        return child
        
    def _expand_with_policy(self, node, state):
         # Expand ALL children using Neural Policy
         policy = self.neural_strategy.predict_policy(state)
         
         if not policy:
              # Fallback to random single expansion
              if not node.untried_moves: return None # Should not happen
              move = random.choice(node.untried_moves)
              state.apply_move(move)
              return self._expand(node, move, state)

         # Create all children
         best_child = None
         max_prior = -1.0
         
         # Untried moves should match policy keys ideally
         # But policy might miss some if mask mismatch (shouldn't happen with correct impl)
         
         # Identify moves to create
         moves_to_expand = list(policy.keys())
         
         # Remove from untried?
         # If we expand all, untried becomes empty.
         node.untried_moves = []
         
         for move_idx in moves_to_expand:
              prob = policy[move_idx]
              
              child = MCTSNode(move_idx=move_idx, parent=node, prior=prob)
              # Child untried moves will be populated when it is expanded later
              # Note: We do NOT populate child.untried_moves here yet to save time?
              # Or we must? UCT logic checks child.untried_moves.
              # Let's populate lazily or now?
              # To populate, we need the state *after* the move.
              # Expanding ALL requires applying ALL moves? That is expensive (n clones).
              # OPTIMIZATION: Do not create `untried_moves` yet.
              # Wait, standard MCTS checks `untried_moves` to decide if leaf.
              # If `untried_moves` is None, it means uninitialized?
              # My MCTSNode `untried_moves` is None by default.
              # Solver code: `while node.untried_moves == [] and node.children:`
              # If `untried_moves` is None, it is falsy? `[]` is falsy.
              # I need to distinguish "Expanded" vs "Unexpanded".
              # Let's assume `untried_moves` being None means unexpanded?
              # Current code: `root_node.untried_moves = root_state.get_legal_moves()`
              
              # If I expand all, I add them to `node.children`.
              node.children[move_idx] = child
              
              if prob > max_prior:
                   max_prior = prob
                   best_child = child
                   
         # Pick the best child to continue this simulation iteration
         # We need to update 'state' to match this child for the rollout phase?
         # The caller `search_with_details` loop:
         # 2. Expansion -> returns node.
         # 3. Simulation -> `while not state.is_terminal(): ...`
         # Wait, the `state` passed to Expand is the PARENT state.
         # We need to apply the move to `state` before returning, so Simulation continues from Child State.
         
         if best_child:
              state.apply_move(best_child.move_idx)
              # Initialize child's untried moves now that we have its state?
              # We can do `child.untried_moves = state.get_legal_moves()`
              best_child.untried_moves = state.get_legal_moves()
              return best_child
              
         return None

    def _expand_all_children(self, node, state):
         """Populates children of node with priors from policy."""
         policy = self.neural_strategy.predict_policy(state)
         if not policy: return
         
         node.untried_moves = []
         for move_idx, prob in policy.items():
              child = MCTSNode(move_idx=move_idx, parent=node, prior=prob)
              node.children[move_idx] = child
              # We don't populate grand-children untried_moves here.
              # They will be populated when visited.
              pass

    def _backpropagate(self, node, reward):
        while node:
            node.visits += 1
            node.wins += reward
            node = node.parent
