import os
from PIL import Image, ImageDraw, ImageFont

# Canvas Setup
CARD_WIDTH = 200
CARD_HEIGHT = 280
COLS = 13
ROWS = 4
SHEET_WIDTH = CARD_WIDTH * COLS
SHEET_HEIGHT = CARD_HEIGHT * ROWS

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 20, 60) # Crimson Red
GRAY = (200, 200, 200)

# Suits & Ranks
# Row 0: Hearts (Red)
# Row 1: Diamonds (Red)
# Row 2: Clubs (Black)
# Row 3: Spades (Black)
# My Code Logic: Hearts=0, Diamonds=1, Clubs=2, Spades=3
SUITS = [
    {'symbol': '♥', 'color': RED, 'name': 'Hearts'},
    {'symbol': '♦', 'color': RED, 'name': 'Diamonds'},
    {'symbol': '♣', 'color': BLACK, 'name': 'Clubs'},
    {'symbol': '♠', 'color': BLACK, 'name': 'Spades'}
]
RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']

# Determine Output Path
OUTPUT_PATH = r"c:\Users\MiEXCITE\Downloads\py4web\examples\react-py4web\frontend\public\react-py4web\static\build\cards.png"
OUTPUT_DIR = os.path.dirname(OUTPUT_PATH)

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Initialize Image
sprite_sheet = Image.new('RGBA', (SHEET_WIDTH, SHEET_HEIGHT), (0, 0, 0, 0))
draw_sheet = ImageDraw.Draw(sprite_sheet)

# Font Loading (Try to find a system font or use default)
try:
    # Windows typically has arial
    font_rank = ImageFont.truetype("arial.ttf", 60)
    font_suit = ImageFont.truetype("arial.ttf", 100) # Big suit center
    font_corner = ImageFont.truetype("arial.ttf", 30) # Small corner suit
    font_court = ImageFont.truetype("times.ttf", 120) # Letter for court
except IOError:
    font_rank = ImageFont.load_default()
    font_suit = ImageFont.load_default()
    font_corner = ImageFont.load_default()
    font_court = ImageFont.load_default()

def draw_card(rank_idx, suit_idx):
    rank_str = RANKS[rank_idx]
    suit_info = SUITS[suit_idx]
    
    # Calculate position
    x_offset = rank_idx * CARD_WIDTH
    y_offset = suit_idx * CARD_HEIGHT
    
    # Create card face
    # Draw White Background with border
    # Use a SAFE_MARGIN to prevent bleeding
    MARGIN = 4
    
    draw_sheet.rectangle(
        [x_offset + MARGIN, y_offset + MARGIN, x_offset + CARD_WIDTH - MARGIN, y_offset + CARD_HEIGHT - MARGIN], 
        fill=WHITE, 
        outline=GRAY, 
        width=2
    )
    
    # Draw Corner Rank (Top Left)
    draw_sheet.text(
        (x_offset + MARGIN + 6, y_offset + MARGIN + 6), 
        rank_str, 
        font=font_rank, 
        fill=suit_info['color']
    )
    
    # Draw Corner Suit (Below Rank)
    draw_sheet.text(
        (x_offset + MARGIN + 10, y_offset + MARGIN + 60), 
        suit_info['symbol'], 
        font=font_corner, 
        fill=suit_info['color']
    )
    
    # Draw Center
    # For J, Q, K -> Draw Big Letter + Suit? Or a "Court" Box?
    # For A -> Big Suit
    # For others -> Number of pips (Too hard to code perfect pips now).
    # Strategy: Big Center Text for Rank + Big Suit below it.
    
    # Center Coordinates
    cx = x_offset + CARD_WIDTH // 2
    cy = y_offset + CARD_HEIGHT // 2
    
    rank_bbox = draw_sheet.textbbox((0, 0), rank_str, font=font_rank)
    rank_w = rank_bbox[2] - rank_bbox[0]
    
    suit_bbox = draw_sheet.textbbox((0, 0), suit_info['symbol'], font=font_suit)
    suit_w = suit_bbox[2] - suit_bbox[0]
    suit_h = suit_bbox[3] - suit_bbox[1]

    # Draw Big Suit in Center
    draw_sheet.text(
        (cx - suit_w // 2, cy - suit_h // 2), 
        suit_info['symbol'], 
        font=font_suit, 
        fill=suit_info['color']
    )
    
    # Invert for bottom right? No, just keep it simple classic.
    # Bottom Right Rank/Suit inverted is classic.
    # Let's Skip inversion logic for now or try simple rotation is hard on single canvas object.
    # Just standard top-left + center is enough for gameplay visibility.

    # Border Inner (to make it look like a card)
    draw_sheet.rectangle(
        [x_offset + 5, y_offset + 5, x_offset + CARD_WIDTH - 5, y_offset + CARD_HEIGHT - 5],
        outline=None,
        width=0
    )

# Execution Loop
print("Generating 52 cards...")
for r in range(ROWS):
    for c in range(COLS):
        draw_card(c, r)

print(f"Saving to {OUTPUT_PATH}")
sprite_sheet.save(OUTPUT_PATH)
# Also save to source public for dev
source_path = r"c:\Users\MiEXCITE\Downloads\py4web\examples\react-py4web\frontend\public\cards.png"
sprite_sheet.save(source_path)
print(f"Also saved to {source_path}")
