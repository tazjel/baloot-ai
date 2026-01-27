
import math
import random
import time
from typing import Dict, List, Optional
from ai_worker.mcts.fast_game import FastGame

class MCTSNode:
    def __init__(self, move_idx: int, parent=None):
        self.move_idx = move_idx # The move that led to this node (Card Index in Hand)
        self.parent = parent
        self.children = {} # Map[move_idx] -> MCTSNode
        self.wins = 0.0
        self.visits = 0
        self.untried_moves = None # populate on first expansions

class MCTSSolver:
    def __init__(self, exploration_constant=1.414):
        self.exploration_constant = exploration_constant

    def search(self, root_state: FastGame, timeout_ms: int = 100) -> int:
        """
        Runs MCTS for a specified valid time.
        Returns the best move index.
        """
        root_node = MCTSNode(move_idx=-1)
        root_node.untried_moves = root_state.get_legal_moves()
        
        start_time = time.time()
        iterations = 0
        
        return self.search_with_details(root_state, timeout_ms)[0]

    def search_with_details(self, root_state: FastGame, timeout_ms: int = 100):
        """
        Runs MCTS and returns (best_move_idx, detailed_stats).
        stats: dict[move_idx] -> { 'visits': int, 'wins': float, 'win_rate': float }
        """
        root_node = MCTSNode(move_idx=-1)
        root_node.untried_moves = root_state.get_legal_moves()
        
        start_time = time.time()
        iterations = 0
        
        while (time.time() - start_time) * 1000 < timeout_ms:
            iterations += 1
            node = root_node
            state = root_state.clone()
            
            # 1. Selection
            while node.untried_moves == [] and node.children:
                is_us_turn = (state.teams[state.current_turn] == 'us')
                node = self._select_child(node, is_us_turn)
                state.apply_move(node.move_idx)
                
            # 2. Expansion
            if node.untried_moves:
                move = random.choice(node.untried_moves)
                state.apply_move(move)
                node = self._expand(node, move, state)
                
            # 3. Simulation (Rollout)
            # Optimized rollout?
            # For now standard random
            steps = 0
            while not state.is_terminal():
                legal = state.get_legal_moves()
                if not legal: break
                move_idx = random.choice(legal)
                state.apply_move(move_idx)
                steps += 1
                
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
                'win_rate': win_rate
            }
            
        return best_move, details

    def _select_child(self, node, is_us_turn: bool):
        # Upper Confidence Bound (UCB1)
        # Adversarial: 
        # If is_us_turn: Maximize (wins/visits)
        # If not is_us_turn (Opponent): Maximize (1 - wins/visits) [Minimax style]
        
        best_score = float('-inf')
        best_child = None
        
        for child in node.children.values():
            exploit = child.wins / child.visits
            
            if not is_us_turn:
                # Opponent wants to minimize 'us' score (maximize '1 - us')
                exploit = 1.0 - exploit
                
            ucb = exploit + self.exploration_constant * math.sqrt(2 * math.log(node.visits) / child.visits)
            
            if ucb > best_score:
                best_score = ucb
                best_child = child
                
        return best_child

    def _expand(self, node, move_idx, state):
        child = MCTSNode(move_idx=move_idx, parent=node)
        child.untried_moves = state.get_legal_moves()
        node.untried_moves.remove(move_idx)
        node.children[move_idx] = child
        return child

    def _backpropagate(self, node, reward):
        while node:
            node.visits += 1
            node.wins += reward
            node = node.parent
