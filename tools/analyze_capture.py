"""Quick analysis of captured Kammelna game data."""
import json
import sys
from collections import Counter

def analyze(path):
    with open(path, 'r', encoding='utf-8') as f:
        d = json.load(f)
    
    ws = d['websocket_traffic']
    sends = [m for m in ws if m['type'] == 'SEND']
    recvs = [m for m in ws if m['type'] == 'RECV']
    connects = [m for m in ws if m['type'] == 'CONNECT']
    
    print(f"{'='*60}")
    print(f"  KAMMELNA CAPTURE ANALYSIS")
    print(f"{'='*60}")
    print(f"  Captured: {d.get('captured_at', 'N/A')}")
    print(f"  Label: {d.get('label', 'N/A')}")
    print(f"  Total WS: {len(ws)} | SEND: {len(sends)} | RECV: {len(recvs)}")
    print(f"  Connections: {len(connects)} | XHR: {d.get('xhr_requests', 0)}")
    
    print(f"\n{'='*60}")
    print(f"  CONNECTIONS")
    print(f"{'='*60}")
    for c in connects:
        url = c['url']
        if 'socialhub' in url.lower():
            print(f"  [SignalR Social] {url[:80]}...")
        elif 'websocket' in url.lower():
            print(f"  [Game Binary] {url}")
        else:
            print(f"  [Unknown] {url[:80]}")
    
    # Analyze game actions from hex data
    print(f"\n{'='*60}")
    print(f"  GAME ACTIONS (from binary messages)")
    print(f"{'='*60}")
    
    action_strings = [
        'a_bid', 'a_card_played', 'a_cards_eating', 'a_accept_next_move',
        'a_back', 'find_match', 'game_loaded', 'game_state', 'game_stat',
        'switch_seat', 'hokom', 'pass', 'chat', 'sira'
    ]
    
    for action in action_strings:
        count = sum(1 for m in ws if action in str(m.get('data', '')))
        if count > 0:
            print(f"  {action:25s}: {count}")
    
    # Analyze SignalR JSON messages
    print(f"\n{'='*60}")
    print(f"  SIGNALR JSON MESSAGES")
    print(f"{'='*60}")
    json_msgs = [m for m in ws if isinstance(m.get('data', ''), str) and m.get('data', '').startswith('{')]
    print(f"  Total JSON messages: {len(json_msgs)}")
    for m in json_msgs[:5]:
        data = m['data'].rstrip('\x1e')
        print(f"  [{m['type']}] {data}")
    
    # Analyze decoded text (Arabic chat messages, player names, etc.)
    print(f"\n{'='*60}")
    print(f"  DECODED TEXT SAMPLES")
    print(f"{'='*60}")
    text_msgs = []
    for m in ws:
        data = str(m.get('data', ''))
        if 'msg' in data and ('\\u' in data or any(ord(c) > 127 for c in data)):
            # Find msg content
            idx = data.find('msg')
            if idx >= 0:
                snippet = data[idx:idx+100].replace('\n', ' ')
                text_msgs.append((m['type'], snippet))
    
    print(f"  Found {len(text_msgs)} chat/text messages")
    for typ, txt in text_msgs[:10]:
        print(f"  [{typ}] ...{txt}...")
    
    # Card analysis
    print(f"\n{'='*60}")
    print(f"  CARD IDENTIFIERS FOUND")
    print(f"{'='*60}")
    cards = []
    for m in ws:
        data = str(m.get('data', ''))
        if 'card' in data and m['type'] == 'SEND':
            # Look for card codes like da, h7, cj, etc.
            idx = data.find('card')
            if idx >= 0:
                snippet = data[idx:idx+30]
                cards.append(snippet)
    
    print(f"  Cards played by user: {len(cards)}")
    for c in cards[:20]:
        print(f"    {c}")
    
    # Game mode
    print(f"\n{'='*60}")
    print(f"  GAME MODE")
    print(f"{'='*60}")
    hokom_count = sum(1 for m in ws if 'hokom' in str(m.get('data', '')))
    sun_count = sum(1 for m in ws if 'sun' in str(m.get('data', '')) and 'Baloot' not in str(m.get('data', '')))
    print(f"  hokom references: {hokom_count}")
    print(f"  sun references: {sun_count}")
    
    # Timeline
    print(f"\n{'='*60}")
    print(f"  GAME TIMELINE")
    print(f"{'='*60}")
    if ws:
        t_start = ws[0]['t']
        t_end = ws[-1]['t']
        duration = (t_end - t_start) / 1000
        print(f"  Duration: {duration:.0f} seconds ({duration/60:.1f} minutes)")
        print(f"  Start: {ws[0].get('type', '')} -> {str(ws[0].get('url', ws[0].get('data', '')))[:60]}")
        print(f"  End:   {ws[-1].get('type', '')} -> {str(ws[-1].get('data', ''))[:60]}")

    # XHR summary
    print(f"\n{'='*60}")
    print(f"  XHR REQUESTS")
    print(f"{'='*60}")
    xhr = d.get('xhr_traffic', [])
    for x in xhr:
        url = x.get('url', 'N/A')
        method = x.get('method', '?')
        status = x.get('status', '?')
        # trim URL
        if len(url) > 80:
            url = url[:77] + '...'
        print(f"  [{method} {status}] {url}")

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'captures/game_capture_v3_autosave_25_20260214_213932.json'
    analyze(path)
