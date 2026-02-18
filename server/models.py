"""
This file defines the database models
"""

from server.common import db, Field
from pydal.validators import *
import datetime

### Define your table below
#
# db.define_table('thing', Field('name'))
#
## always commit your models to avoid problems later
#
# db.commit()
#
# Define the user table (using default auth or matching legacy foo for now)
db.define_table('app_user',
                Field('first_name', required=True),
                Field('last_name', required=True),
                Field('email', unique=True, required=True),
                Field('password', 'password', readable=False, required=True),
                Field('league_points', 'integer', default=1000),
                Field('is_active', 'boolean', default=True),
                Field('created_on', 'datetime', default=lambda: datetime.datetime.now()),
                Field('updated_on', 'datetime', default=lambda: datetime.datetime.now(), update=lambda: datetime.datetime.now()),
                )

# Define game results table
db.define_table('game_result',
                Field('user_id', 'reference app_user'),
                Field('user_email'), # Simple linkage for now
                Field('score_us', 'integer'),
                Field('score_them', 'integer'),
                Field('is_win', 'boolean'),
                Field('timestamp', 'datetime', default=lambda: datetime.datetime.now())
                )

# Define bot training data table
db.define_table('bot_training_data',
                Field('context_hash', required=True), # Unique hash of the game state
                Field('game_state_json', 'text'),     # Full snapshot for replay
                Field('bad_move_json', 'text'),       # The move the bot wanted to make
                Field('correct_move_json', 'text'),   # The move the user corrected it to
                Field('reason', 'text'),              # User's explanation
                Field('image_filename', 'string'),    # Link to source screenshot (Data Flywheel)
                Field('created_on', 'datetime', default=lambda: datetime.datetime.now())
                )

# Define match archive for Replay Studio
db.define_table('match_archive',
                Field('game_id', unique=True, required=True),
                Field('user_id', 'reference app_user'),
                Field('user_email'), # Optional linkage
                Field('history_json', 'text'), # Full JSON blob
                Field('final_score_us', 'integer'),
                Field('final_score_them', 'integer'),
                Field('timestamp', 'datetime', default=lambda: datetime.datetime.now())
                )

db.commit()