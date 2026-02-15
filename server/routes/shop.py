"""
Shop and Inventory routes.
"""
import logging
from py4web import action, request, response, abort
from server.common import db
from server.routes.auth import token_required

logger = logging.getLogger(__name__)

@action('shop/purchase', method=['POST'])
@token_required
@action.uses(db)
def purchase_item():
    user_id = request.user.get('user_id')
    data = request.json
    item_id = data.get('itemId')
    cost = data.get('cost')

    if not item_id or cost is None:
        abort(400, "Missing itemId or cost")

    user = db.app_user(user_id)
    if not user:
        abort(404, "User not found")

    if user.coins < cost:
        abort(400, "Insufficient funds")

    # Update owned items
    owned = user.owned_items or []
    # Ensure owned is a list (pydal json handling)
    if not isinstance(owned, list):
        owned = []

    if item_id in owned:
         # Already owned
         pass
    else:
        owned.append(item_id)

    user.update_record(coins=user.coins - cost, owned_items=owned)

    return {"success": True, "coins": user.coins, "ownedItems": owned}

@action('shop/equip', method=['POST'])
@token_required
@action.uses(db)
def equip_item():
    user_id = request.user.get('user_id')
    data = request.json
    item_id = data.get('itemId')
    item_type = data.get('type') # 'card' or 'table'

    if not item_id or not item_type:
        abort(400, "Missing itemId or type")

    user = db.app_user(user_id)
    if not user:
        abort(404, "User not found")

    owned = user.owned_items or []
    if not isinstance(owned, list):
        owned = []

    if item_id not in owned:
        abort(400, "Item not owned")

    equipped = user.equipped_items or {}
    if not isinstance(equipped, dict):
        equipped = {}

    equipped[item_type] = item_id

    user.update_record(equipped_items=equipped)

    return {"success": True, "equippedItems": equipped}

def bind_shop(safe_mount):
    safe_mount('/shop/purchase', 'POST', purchase_item)
    safe_mount('/shop/equip', 'POST', equip_item)
