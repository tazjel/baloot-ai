"""
Shop routes: purchase, equip.
"""
import logging
from py4web import action, request, response, abort
from server.common import db
from server.routes.auth import token_required
from gevent.lock import RLock

logger = logging.getLogger(__name__)

# Global lock to prevent race conditions in single-process gevent environment
_shop_lock = RLock()

# Basic item catalog for demo purposes
# In production, this should be in a database table 'shop_items'
ITEM_PRICES = {
    'golden_card': 500,
    'diamond_table': 2000,
    'neon_frame': 300,
    'avatar_vip': 1000,
    'card_default': 0,
    'table_default': 0
}

@action('shop/purchase', method=['POST'])
@action.uses(db)
@token_required
def purchase():
    data = request.json
    if not data:
        abort(400, "Invalid JSON")

    item_id = data.get('itemId')

    if not item_id:
        response.status = 400
        return {"error": "Missing item_id"}

    cost = ITEM_PRICES.get(item_id)
    if cost is None:
        response.status = 404
        return {"error": "Item not found"}

    user_id = request.user.get('user_id')

    # Use global lock for critical section (read-check-update)
    with _shop_lock:
        # Re-fetch user record inside lock to ensure fresh data
        user_record = db.app_user(user_id)

        if not user_record:
            response.status = 404
            return {"error": "User not found"}

        current_coins = user_record.coins or 0
        if current_coins < cost:
            response.status = 400
            return {"error": "Insufficient coins"}

        # Update logic
        owned_items = user_record.owned_items or []

        # Ensure it's a list
        if not isinstance(owned_items, list):
            owned_items = []

        if item_id in owned_items:
            return {
                "message": "Item already owned",
                "coins": current_coins,
                "ownedItems": owned_items
            }

        new_coins = current_coins - cost
        owned_items.append(item_id)

        user_record.update_record(coins=new_coins, owned_items=owned_items)

        return {
            "message": "Purchase successful",
            "coins": new_coins,
            "ownedItems": owned_items
        }

@action('shop/equip', method=['POST'])
@action.uses(db)
@token_required
def equip():
    data = request.json
    if not data:
        abort(400, "Invalid JSON")

    item_id = data.get('itemId')
    item_type = data.get('type') # 'card' or 'table'

    if not item_id or item_type not in ['card', 'table']:
        response.status = 400
        return {"error": "Invalid item_id or type"}

    user_id = request.user.get('user_id')
    user_record = db.app_user(user_id)

    if not user_record:
        response.status = 404
        return {"error": "User not found"}

    owned_items = user_record.owned_items or []
    # Defaults are always owned
    is_default = item_id in ['card_default', 'table_default']

    if not is_default and item_id not in owned_items:
        response.status = 403
        return {"error": "Item not owned"}

    equipped = user_record.equipped_items or {}
    if not isinstance(equipped, dict):
        equipped = {'card': 'card_default', 'table': 'table_default'}

    equipped[item_type] = item_id

    user_record.update_record(equipped_items=equipped)

    return {
        "message": "Equip successful",
        "equippedItems": equipped
    }

def bind_shop(safe_mount):
    safe_mount('/shop/purchase', 'POST', purchase)
    safe_mount('/shop/equip', 'POST', equip)
