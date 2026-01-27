
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
        
        while (time.time() - start_time) * 1000 < timeout_ms:
            iterations += 1
            node = root_node
            state = root_state.clone()
            
            # 1. Selection
            while node.untried_moves == [] and node.children:
                node = self._select_child(node)
                state.apply_move(node.move_idx)
                
            # 2. Expansion
            if node.untried_moves:
                move = random.choice(node.untried_moves)
                state.apply_move(move)
                node = self._expand(node, move, state)
                
            # 3. Simulation (Rollout)
            steps = 0
            while not state.is_terminal():
                legal = state.get_legal_moves()
                if not legal: break # Should not happen unless error
                move_idx = random.choice(legal)
                state.apply_move(move_idx)
                steps += 1
                
            # 4. Backpropagation
            # Score perspective: maximize 'us' score
            # Just using Raw Score Difference or Win/Loss?
            # Win/Loss is better for tree search stability usually.
            # But Score matters (26 pts > 16 pts).
            # Let's normalize score: Diff / MaxPossible (~152).
            
            us_score = state.scores['us']
            them_score = state.scores['them']
            
            # Simple Reward: Who won the match? (Or just this partial game?)
            # Partial Game optimization: Maximize score difference.
            score_diff = us_score - them_score
            reward = 0.5 + (score_diff / 50.0) # Normalize loosely. 0.5 is tie.
            if reward > 1.0: reward = 1.0
            if reward < 0.0: reward = 0.0
            
            self._backpropagate(node, reward, state.teams[root_state.current_turn])
            
        # Select best move (highest visits)
        best_move = max(root_node.children.items(), key=lambda item: item[1].visits)[0]
        
        # print(f"MCTS Finished: {iterations} iters, Best Move: {best_move}")
        return best_move

    def _select_child(self, node):
        # Upper Confidence Bound (UCB1)
        # Should select based on perspective of player at this node? 
        # Yes, MCTS usually assumes alternating turns (Minimax style selection if 2-player zero-sum).
        # But Baloot is Team Game (2v2).
        # We assume if it's 'us', we pick max UCB. If 'them', we pick... max UCB for THEM?
        # Simplified UCB usually works if we flip reward.
        # Let's assume standard UCB for now.
        
        best_score = float('-inf')
        best_child = None
        
        for child in node.children.values():
            ucb = (child.wins / child.visits) + \
                  self.exploration_constant * math.sqrt(2 * math.log(node.visits) / child.visits)
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

    def _backpropagate(self, node, reward, root_team):
        # Reward is based on 'us' perspective (0-1).
        # If the player at the node was 'them', they want to minimize 'us' reward?
        # Actually standard MCTS backprop adds reward to all nodes visited.
        # But UCB Selection must be aware of perspective.
        # SIMPLIFICATION: We just accumulate 'us' wins.
        # Selection logic should inverse for opponents. 
        # (TODO: Refine for strict Minimax-MCTS later).
        
        while node:
            node.visits += 1
            node.wins += reward
            node = node.parent
