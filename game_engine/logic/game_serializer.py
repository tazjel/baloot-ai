"""
game_engine/logic/game_serializer.py — Game JSON Serialization
===============================================================

Extracted from game.py to reduce its size. Handles the full
to_json() → from_json() cycle used for Redis persistence.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Any

from game_engine.models.constants import GamePhase
from game_engine.models.deck import Deck
from game_engine.models.player import Player
from game_engine.models.card import Card as CardModel
from game_engine.core.state import GameState
from game_engine.core.graveyard import Graveyard

from .timer_manager import TimerManager
from .trick_manager import TrickManager
from .scoring_engine import ScoringEngine
from .project_manager import ProjectManager
from .qayd_engine import QaydEngine
from .game_lifecycle import GameLifecycle
from .player_manager import PlayerManager
from .phases.challenge_phase import ChallengePhase
from .phases.bidding_phase import BiddingPhase as BiddingLogic
from .phases.playing_phase import PlayingPhase as PlayingLogic

if TYPE_CHECKING:
    from .game import Game


def serialize_game(game: Game) -> dict:
    """Serialize the full game to a JSON-safe dict."""
    player_dicts = []
    for p in game.players:
        player_dicts.append({
            'id': p.id, 'name': p.name,
            'index': p.index, 'avatar': getattr(p, 'avatar', None),
            'is_bot': p.is_bot,
            'position': p.position,
            'team': p.team,
            'hand': [c.to_dict() for c in p.hand] if p.hand else [],
            'captured_cards': [c.to_dict() if hasattr(c, 'to_dict') else c for c in getattr(p, 'captured_cards', [])],
            'action_text': getattr(p, 'action_text', ''),
        })

    tc_dicts = []
    for tc in game.table_cards:
        card = tc.get('card') or tc
        if hasattr(card, 'suit'):
            card = {'suit': card.suit, 'rank': card.rank}
        tc_dicts.append({
            'card': card,
            'playedBy': tc.get('playedBy'),
            'playerId': tc.get('playerId'),
            'metadata': tc.get('metadata'),
        })

    return {
        '_version': 2,
        'state': game.state.model_dump(mode='json'),
        'players': player_dicts,
        'table_cards': tc_dicts,
        'timer_paused': game.timer_paused,
        'turn_duration': game.turn_duration,
        'timer_state': {
            'active': game.timer.active,
            'start_time': game.timer.start_time,
            'duration': game.timer.duration,
            'paused': getattr(game.timer, 'paused', False),
            'paused_at': getattr(game.timer, 'paused_at', 0),
        },
        'bidding_engine': game.bidding_engine.to_dict() if game.bidding_engine else None,
        'floor_card': game._floor_card_obj.to_dict() if game._floor_card_obj else None,
        'qayd_state': game.qayd_engine.state if game.qayd_engine else None,
    }


def deserialize_game(data: dict) -> Game:
    """Reconstruct a full Game object from a JSON dict."""
    from .game import Game

    state_data = data['state']

    game = Game.__new__(Game)
    game.state = GameState(**state_data)
    game._floor_card_obj = None
    game.deck = Deck()

    # Restore table cards
    game.table_cards = []
    for tc in data.get('table_cards', []):
        card_d = tc.get('card', tc)
        game.table_cards.append({
            'card': CardModel(card_d['suit'], card_d['rank']),
            'playedBy': tc.get('playedBy'),
            'playerId': tc.get('playerId'),
            'metadata': tc.get('metadata'),
        })

    # Restore timer
    game.timer = TimerManager(5)
    timer_state = data.get('timer_state')
    if timer_state:
        game.timer.active = timer_state.get('active', False)
        game.timer.start_time = timer_state.get('start_time', 0)
        game.timer.duration = timer_state.get('duration', 5)
        game.timer.paused = timer_state.get('paused', False)
        game.timer.paused_at = timer_state.get('paused_at', 0)
    game.timer_paused = data.get('timer_paused', False)
    game.turn_duration = data.get('turn_duration', 30)
    game.bidding_engine = None  # Reconstructed below after players are loaded

    # Restore players
    game.players = []
    for pd in data.get('players', []):
        p = Player(pd['id'], pd['name'], pd['index'], game, avatar=pd.get('avatar'))
        p.is_bot = pd.get('is_bot', False)
        for cd in pd.get('hand', []):
            p.hand.append(CardModel(cd['suit'], cd['rank']))
        for cd in pd.get('captured_cards', []):
            if isinstance(cd, dict) and 'suit' in cd:
                p.captured_cards.append(CardModel(cd['suit'], cd['rank']))
        p.action_text = pd.get('action_text', '')
        game.players.append(p)

    # Restore floor card
    fc_data = data.get('floor_card')
    if fc_data:
        game._floor_card_obj = CardModel(fc_data['suit'], fc_data['rank'])
    else:
        game._floor_card_obj = None

    # Remove dealt cards from deck to prevent duplicates
    dealt_ids = set()
    for p in game.players:
        for c in p.hand:
            dealt_ids.add(c.id)
        for c in p.captured_cards:
            dealt_ids.add(c.id)
    for tc in game.table_cards:
        card = tc.get('card')
        if card and hasattr(card, 'id'):
            dealt_ids.add(card.id)
    if game._floor_card_obj:
        dealt_ids.add(game._floor_card_obj.id)
    game.deck.cards = [c for c in game.deck.cards if c.id not in dealt_ids]

    # Rebuild managers
    game.graveyard = Graveyard()
    for trick in game.round_history:
        game.graveyard.commit_trick(trick.get('cards', []))
    game.lifecycle = GameLifecycle(game)
    game.player_manager = PlayerManager(game)
    game.trick_manager = TrickManager(game)
    game.scoring_engine = ScoringEngine(game)
    game.project_manager = ProjectManager(game)
    game.challenge_phase = ChallengePhase(game)
    game.qayd_engine = QaydEngine(game)

    # Restore qayd state from serialized data
    saved_qayd = data.get('qayd_state')
    if saved_qayd and saved_qayd.get('active'):
        game.qayd_engine.state.update(saved_qayd)
    game.qayd_state = game.qayd_engine.state

    # Phase handlers
    game.phases = {
        GamePhase.BIDDING.value:   BiddingLogic(game),
        GamePhase.PLAYING.value:   PlayingLogic(game),
        GamePhase.CHALLENGE.value: game.challenge_phase,
    }

    # Reconstruct BiddingEngine if we were in BIDDING phase
    be_data = data.get('bidding_engine')
    if be_data and game.players:
        from .bidding_engine import BiddingEngine
        game.bidding_engine = BiddingEngine.from_dict(be_data, game.players)

    # Recorder
    try:
        from server.common import redis_client
        from game_engine.core.recorder import TimelineRecorder
        game.recorder = TimelineRecorder(redis_client)
    except Exception:
        game.recorder = None

    return game
