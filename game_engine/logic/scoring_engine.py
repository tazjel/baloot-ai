from typing import Dict, List, Tuple
from server.logging_utils import logger

class ScoringEngine:
    def __init__(self, game):
        self.game = game

    def resolve_project_scores(self) -> Tuple[int, int, List[Dict], List[Dict]]:
        """Resolves Mashaari (Projects) and calculates points."""
        project_abnat_us = 0
        project_abnat_them = 0
        winning_projects_us = []
        winning_projects_them = []

        for pos, projects in self.game.declarations.items():
            player = next((p for p in self.game.players if p.position == pos), None)
            if not player: continue
            
            for proj in projects:
                score = proj['score']
                item = {'type': proj['type'], 'rank': proj['rank'], 'suit': proj.get('suit'), 'owner': pos, 'score': score}
                
                if player.team == 'us':
                    project_abnat_us += score
                    winning_projects_us.append(item)
                else:
                    project_abnat_them += score
                    winning_projects_them.append(item)
                    
        return project_abnat_us, project_abnat_them, winning_projects_us, winning_projects_them

    def calculate_card_abnat(self) -> Tuple[int, int, Dict[str, int]]:
        """Calculates raw card points (Abnat) for both teams including Last Trick bonus."""
        card_abnat_us = 0
        card_abnat_them = 0

        if not self.game.round_history:
            return 0, 0, {'us': 0, 'them': 0}

        for trick in self.game.round_history:
             winner_pos = trick['winner']
             winner_p = next((p for p in self.game.players if p.position == winner_pos), None)
             if not winner_p:
                 continue
             if winner_p.team == 'us': card_abnat_us += trick['points']
             else: card_abnat_them += trick['points']
             
        # Last Trick Bonus (10 Raw Points / Abnat)
        last_trick_bonus = {'us': 0, 'them': 0}
        if self.game.round_history:
            last_winner_pos = self.game.round_history[-1]['winner']
            last_p = next((p for p in self.game.players if p.position == last_winner_pos), None)
            if last_p: 
                 if last_p.team == 'us': last_trick_bonus['us'] = 10
                 else: last_trick_bonus['them'] = 10
        
        card_abnat_us += last_trick_bonus['us']
        card_abnat_them += last_trick_bonus['them']
        
        return card_abnat_us, card_abnat_them, last_trick_bonus

    @staticmethod
    def sun_card_gp(abnat: int) -> int:
        """SUN GP: floor-to-even rounding.

        Validated 100% against 424+ benchmark SUN rounds.
        Formula: q, r = divmod(abnat, 5); q + (1 if q is odd and r > 0).
        """
        q, r = divmod(abnat, 5)
        return q + (1 if q % 2 == 1 and r > 0 else 0)

    @staticmethod
    def hokum_card_gp(abnat: int) -> int:
        """HOKUM GP: individual rounding (round > 5 up).

        Used per-team. Caller must apply sum=16 constraint via
        hokum_pair_gp() for the pair.
        """
        q, r = divmod(abnat, 10)
        return q + (1 if r > 5 else 0)

    @staticmethod
    def hokum_pair_gp(raw_a: int, raw_b: int) -> tuple[int, int]:
        """HOKUM pair-based GP with sum=16 constraint.

        Validated 100% against 1095 benchmark rounds.
        Individual rounding, then adjust if sum != 16:
        - sum=17: reduce side with larger mod-10 remainder;
          on tie, reduce the side with larger GP (higher raw)
        - sum=15: increase side with larger mod-10 remainder;
          on tie, increase the side with larger GP (higher raw)
        """
        gp_a = ScoringEngine.hokum_card_gp(raw_a)
        gp_b = ScoringEngine.hokum_card_gp(raw_b)
        total = gp_a + gp_b
        if total == 17:
            rem_a, rem_b = raw_a % 10, raw_b % 10
            if rem_a > rem_b or (rem_a == rem_b and raw_a >= raw_b):
                gp_a -= 1
            else:
                gp_b -= 1
        elif total == 15:
            rem_a, rem_b = raw_a % 10, raw_b % 10
            if rem_a > rem_b or (rem_a == rem_b and raw_a >= raw_b):
                gp_a += 1
            else:
                gp_b += 1
        return gp_a, gp_b

    def _calculate_score_for_team(self, raw_val: int, mode: str) -> int:
        """Legacy single-team GP conversion (kept for backward compat)."""
        if mode == 'SUN':
            return self.sun_card_gp(raw_val)
        else:
            return self.hokum_card_gp(raw_val)

    def calculate_game_points_with_tiebreak(self, card_points_us, card_points_them, ardh_points_us, ardh_points_them, bidder_team):
        raw_us = card_points_us + ardh_points_us
        raw_them = card_points_them + ardh_points_them

        if self.game.game_mode == 'SUN':
            # SUN: floor-to-even per team, sum should be 26
            gp_us = self.sun_card_gp(raw_us)
            gp_them = self.sun_card_gp(raw_them)
        else:
            # HOKUM: pair-based rounding with sum=16 constraint
            gp_us, gp_them = self.hokum_pair_gp(raw_us, raw_them)

        if gp_us > gp_them:
             winner = 'us'
        elif gp_them > gp_us:
             winner = 'them'
        else:
             winner = bidder_team

        return {
            'game_points': {'us': gp_us, 'them': gp_them},
            'lost_in_rounding': {'us': 0, 'them': 0},
            'counting_team': 'us',
            'winner': winner
        }

    def calculate_final_scores(self):
        """Orchestrates the entire scoring calculation for the round end."""
        
        # 1. Abnat Calculation
        card_abnat_us, card_abnat_them, last_trick_bonus = self.calculate_card_abnat()
        
        # 2. Project Calculation
        project_abnat_us, project_abnat_them, winning_projects_us, winning_projects_them = self.resolve_project_scores()

        # 3. Final Round Score Logic
        total_abnat_us = card_abnat_us + project_abnat_us
        total_abnat_them = card_abnat_them + project_abnat_them

        bidder_pos = self.game.bid.get('bidder')
        bidder_team = 'them' 
        if bidder_pos:
            bidder_p = next((p for p in self.game.players if p.position == bidder_pos), None)
            if bidder_p: bidder_team = bidder_p.team

        game_points_us = 0
        game_points_them = 0
        
        # --- KABOOT CHECK ---
        tricks_us = sum(1 for t in self.game.round_history if next(p for p in self.game.players if p.position == t['winner']).team == 'us')
        tricks_them = sum(1 for t in self.game.round_history if next(p for p in self.game.players if p.position == t['winner']).team == 'them')
        
        kaboot_winner = None
        if tricks_them == 0 and tricks_us > 0: kaboot_winner = 'us'
        elif tricks_us == 0 and tricks_them > 0: kaboot_winner = 'them'
        
        ardh_us = last_trick_bonus['us']
        ardh_them = last_trick_bonus['them']
        
        pure_card_us = card_abnat_us - ardh_us
        pure_card_them = card_abnat_them - ardh_them

        if kaboot_winner:
            if self.game.game_mode == 'SUN':
                if kaboot_winner == 'us': game_points_us = 44
                else: game_points_them = 44
            else: # HOKUM
                if kaboot_winner == 'us': game_points_us = 25
                else: game_points_them = 25
        else:
            gp_result = self.calculate_game_points_with_tiebreak(
                pure_card_us, pure_card_them,
                ardh_us, ardh_them,
                bidder_team
            )
            
            game_points_us = gp_result['game_points']['us']
            game_points_them = gp_result['game_points']['them']
        
        # Add Project Game Points (Applied to both Kaboot and Normal results)
        if self.game.game_mode == 'SUN':
            proj_gp_us = (project_abnat_us * 2) // 10
            proj_gp_them = (project_abnat_them * 2) // 10
        else:
            proj_gp_us = project_abnat_us // 10
            proj_gp_them = project_abnat_them // 10
        
        game_points_us += proj_gp_us
        game_points_them += proj_gp_them

        score_us = game_points_us
        score_them = game_points_them
            
        # Khasara Check — validated against benchmark rules:
        # 1. bidder_gp < opp_gp → khasara
        # 2. GP tie: compare raw abnat totals
        #    - Normal: bid_total_raw <= opp_total_raw → bidder loses
        #    - Doubled: doubler loses (whoever declared hokomclose/beforeyou)
        # 3. Equal raw on tie → split (both keep GP, no khasara)
        khasara = False

        if self.game.sawa_failed_khasara:
            khasara = True
            claimer_pos = self.game.sawa_state.claimer
            if claimer_pos in ['Bottom', 'Top']: bidder_team = 'us'
            else: bidder_team = 'them'
        elif not kaboot_winner:
            bidder_score = score_us if bidder_team == 'us' else score_them
            opp_score = score_them if bidder_team == 'us' else score_us
            if bidder_score < opp_score:
                khasara = True
            elif bidder_score == opp_score:
                # GP tie: compare raw abnat totals
                bidder_raw = total_abnat_us if bidder_team == 'us' else total_abnat_them
                opp_raw = total_abnat_them if bidder_team == 'us' else total_abnat_us
                is_doubled = self.game.doubling_level >= 2
                if is_doubled:
                    # Doubled rounds: doubler always loses the tie
                    khasara = True
                elif bidder_raw < opp_raw:
                    # Normal: bidder loses if raw abnat is strictly less
                    khasara = True
                # Equal raw on tie → split (no khasara)
                
        # Apply Khasara Penalty
        if khasara: 
            total_pot = score_us + score_them
            if bidder_team == 'us':
                score_us = 0
                score_them = total_pot
            else:
                score_them = 0
                score_us = total_pot
        
        # Doubling (Gahwa Chain)
        multiplier = 1
        if self.game.doubling_level >= 2:
            if self.game.doubling_level >= 100: # GAHWA 
                multiplier = 1 
                if score_us > 0 and score_them == 0: 
                    score_us = 152
                elif score_them > 0 and score_us == 0:
                    score_them = 152
            else:
                multiplier = self.game.doubling_level # 2, 3, 4
                score_us *= multiplier
                score_them *= multiplier
        
        # Baloot Declaration (K+Q of trump) — IMMUNE to doubling
        # Always exactly 2 GP per declaration, added AFTER multiplier
        baloot_gp_us = 0
        baloot_gp_them = 0
        baloot_declarations = []
        try:
            if hasattr(self.game, 'baloot_manager'):
                baloot_pts = self.game.baloot_manager.get_baloot_points()
                baloot_gp_us = baloot_pts.get('us', 0)
                baloot_gp_them = baloot_pts.get('them', 0)
                baloot_declarations = self.game.baloot_manager.get_declarations()
                score_us += baloot_gp_us
                score_them += baloot_gp_them
                if baloot_gp_us or baloot_gp_them:
                    logger.info(f"[BALOOT] Scoring: us +{baloot_gp_us} GP, them +{baloot_gp_them} GP (immune to doubling)")
        except Exception as e:
            logger.error(f"Baloot scoring error: {e}")

        is_kaboot_us = (kaboot_winner == 'us')
        is_kaboot_them = (kaboot_winner == 'them')

        round_result = {
            'roundNumber': len(self.game.past_round_results) + 1,
            'bid': self.game.bid, 
            'us': {
                'aklat': pure_card_us, 
                'ardh': ardh_us,
                'projectPoints': project_abnat_us,
                'abnat': card_abnat_us + project_abnat_us, 
                'result': score_us,
                'isKaboot': is_kaboot_us,
                'multiplierApplied': multiplier,
                'projects': winning_projects_us
            },
            'them': {
                'aklat': pure_card_them,
                'ardh': ardh_them,
                'projectPoints': project_abnat_them,
                'abnat': card_abnat_them + project_abnat_them, 
                'result': score_them,
                'isKaboot': is_kaboot_them,
                'multiplierApplied': multiplier,
                'projects': winning_projects_them
            },
            'winner': 'us' if score_us > score_them else 'them',
            'baida': (score_us == score_them),
            'project': self.game.game_mode,
            'balootDeclarations': baloot_declarations,
        }
        
        return round_result, score_us, score_them
