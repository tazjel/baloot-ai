from server.common import db, logger
from server.logging_utils import log_event, log_error
import json
import datetime

from server.serializers import serialize

def archive_match(game_instance):
    """
    Saves the full match history of a completed game to the database.
    """
    try:
        if not game_instance.full_match_history:
            log_event("ARCHIVE_SKIPPED", game_instance.room_id, details={"reason": "No history"})
            return

        # Check if already exists? (Maybe updated?)
        existing = db.match_archive(game_id=game_instance.room_id)
        if existing:
             # Update?
             pass
        
        # Serialize history
        # Ensure deep serialization if objects exist (though Game.end_round usually handles to_dict)
        data = serialize(game_instance.full_match_history)
        history_json = json.dumps(data)
        
        db.match_archive.insert(
            game_id=game_instance.room_id,
            user_email=None, # Update if we can link to a user later
            history_json=history_json,
            final_score_us=game_instance.match_scores['us'],
            final_score_them=game_instance.match_scores['them'],
            timestamp=datetime.datetime.now()
        )
        db.commit()
        log_event("MATCH_ARCHIVED", game_instance.room_id, details={
            "final_scores": game_instance.match_scores, 
            "history_stats": {"rounds": len(game_instance.full_match_history)}
        })
        
    except Exception as e:
        log_error(game_instance.room_id, "Archive Failed", {"error": str(e)})
