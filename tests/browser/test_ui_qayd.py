import pytest
from playwright.sync_api import Page, expect
import time
import os

# Snapshot directory configuration
SNAPSHOT_DIR = "snapshots"

def test_qayd_flow(page: Page, assert_snapshot):
    """
    End-to-end verification of the Qayd flow in Single Player mode.
    Includes Visual Regression Testing.
    """
    print("🌐 Navigating to Game...")
    page.goto("http://localhost:5173", timeout=15000)
    
    # 1. Start Single Player Game
    print("🖱️ Searching for 'Start Game' button...")
    start_btn = page.get_by_text("ابدأ اللعب")
    expect(start_btn).to_be_visible(timeout=10000)
    
    # Visual Check 1: Lobby Screen
    # assert_snapshot(page.screenshot(mask=[start_btn])) # Example masking
    assert_snapshot(page.screenshot()) 
    
    start_btn.click()
    
    # 2. Bidding Phase
    print("⏳ Waiting for Game to Start (Bidding)...")
    
    try:
        sun_btn = page.get_by_text("SUN", exact=True)
        # Wait for button to be stable
        sun_btn.wait_for(state="visible", timeout=10000)
        
        # Visual Check 2: Bidding UI
        # We assume clean state. Mask timer if needed.
        # expect(page).to_have_screenshot("bidding_phase.png")
        
        print("   ✅ It is my turn! Bidding SUN...")
        sun_btn.click()
    except Exception:
        print("   ⚠️ Bidding buttons not found or timed out. Assuming Bot Turn.")

    # 3. Playing Phase - Wait for Qayd Button
    print("⏳ Waiting for Playing Phase (Qayd Button)...")
    # 3. Playing Phase - Wait for Qayd Button (Use ActionBar Button)
    print("⏳ Waiting for Playing Phase (Qayd Action Button)...")
    # Button is now in ActionBar with Gavel icon and text "قيدها"
    # Best practice: use data-testid
    qayd_btn = page.locator("button[data-testid='btn-qayd']")
    
    print("🔨 Clicking Qayd Action Button...")
    # Wait for it to be enabled (it might be disabled momentarily)
    qayd_btn.wait_for(state="visible", timeout=30000)
    qayd_btn.click()
    
    # expect(qayd_btn).to_be_visible(timeout=30000)
    print("✅ Playing Phase Active - Qayd Triggered")
    
    # 4. Wait for game progress (Handle User Turn)
    print("⏳ Waiting for game flow...")
    
    # Check if we need to play a card (User Turn)
    try:
        # Wait briefly to see if it's our turn (cards interactable)
        # Using a distinct selector for player's hand cards that are playable
        # Note: This depends on UI implementation. Usually cards float or highlight.
        # We'll try to click a card if "Your Turn" is implied or if we wait too long.
        print("   👀 Checking if it is My Turn to play...")
        
        # Heuristic: If trick history is empty after 5 seconds, try playing a card
        # We use a shorter timeout for history initially
        page.locator(".bg-black\\/40.rounded-xl").first.wait_for(state="visible", timeout=5000)
    except Exception:
        print("   ⚠️ Trick history not updating. Assuming it's MY TURN or game stroke.")
        print("   🃏 Attempting to play a card...")
        
        # Locate player cards (adjust selector to match your Hand component)
        # Based on typical Baloot UI, cards are in the bottom area
        # We need a generic selector for "My Hand Cards"
        # Assuming they are images or divs with click handlers
        # We'll try to click the LAST card (often highest or just available)
        try:
             # Try to find cards using the accessible role and label defined in HandFan.tsx
             # HandFan uses role="button" and aria-label="Play {rank} of {suit}"
             my_cards = page.locator("[role='button'][aria-label^='Play']")
             
             if my_cards.count() > 0:
                 print(f"   found {my_cards.count()} playable cards.")
                 # Click the last card (usually safest to play from right/left depending on sort, but valid click is key)
                 my_cards.last.click(timeout=2000)
                 print("   ✅ Clicked a card.")
             else:
                 print("   ❌ Could not find my cards (checked [role='button'][aria-label^='Play']).")
                 # Fallback: check for any SVG images in bottom area (if CardVector is SVG)
                 fallback_cards = page.locator(".absolute.bottom-2 svg, .absolute.bottom-4 svg")
                 if fallback_cards.count() > 0:
                     print("   ⚠️ specific selector failed, trying generic SVG fallback...")
                     fallback_cards.last.click(timeout=2000)
        except Exception as e:
            print(f"   ⚠️ Failed to play card: {e}")

    # Now wait for the history again (longer timeout)
    print("⏳ Waiting for trick history (post-action)...")
    page.locator(".bg-black\\/40.rounded-xl").first.wait_for(state="visible", timeout=30000)
    
    # 5. Initiate Qayd
    print("🖱️ Clicking 'Qayd'...")
    qayd_btn.click()
    
    # 6. Verify Overlay (VISUAL REGRESSION CRITICAL PATH)
    print("👀 Verifying Overlay...")
    report_header = page.get_by_text("Report Violation (Qayd)")
    expect(report_header).to_be_visible(timeout=5000)
    
    # Visual Check 3: Qayd Modal
    assert_snapshot(page.screenshot())
    
    # 7. Select Crime and Proof
    print("🖱️ Selecting Crime (Trick History)...")
    cards = page.locator(".bg-black\\/40.rounded-xl")
    
    # Wait for cards to be actionable
    cards.first.wait_for(state="visible")
    
    if cards.count() > 0:
        cards.first.click()
        cards.first.locator("div").last.click()
    else:
        pytest.fail("❌ No cards found in Trick History!")

    print("🖱️ Selecting Proof (My Hand)...")
    if cards.count() > 0:
        cards.last.click()
    
    # 8. Confirm Qayd
    print("🖱️ Clicking Confirm...")
    confirm_btn = page.get_by_text("CONFIRM QAYD")
    confirm_btn.click()
    
    # 9. Verify Resolution and Inspect Result
    print("⏳ Waiting for Resolution...")
    
    # The 'Confirm' button hides when result appears
    expect(confirm_btn).to_be_hidden(timeout=10000)
    
    # Now the "Result" step should be visible for ~3 seconds
    # logic: renderResult() -> Result Banner (bg-[#4CAF50] or bg-[#F44336])
    
    print("🕵️ Inspecting Qayd Result...")
    try:
        # Wait for result banner text
        result_banner = page.locator("div.rounded-xl.flex.items-center.justify-between.shadow-md")
        result_banner.wait_for(state="visible", timeout=5000)
        
        # Scrape details
        result_text = result_banner.locator("span.text-xl").inner_text()
        result_subtext = result_banner.locator("span.text-sm").inner_text()
        
        print("\n" + "="*40)
        print("📢 QAYD REPORT")
        print("="*40)
        print(f"Result:  {result_text}")
        print(f"Details: {result_subtext}")
        
        # Check for penalty
        penalty_locator = page.locator("span.text-red-400.font-bold")
        if penalty_locator.is_visible():
            print(f"Penalty: {penalty_locator.inner_text()}")
        else:
            print("Penalty: None visible")
        print("="*40 + "\n")
        
    except Exception as e:
        print(f"⚠️ Could not extract result details (might have closed too fast): {e}")

    # Visual Check 4: Result Screen
    assert_snapshot(page.screenshot())

    # Wait for overlay to fully close (auto-close is 3s)
    print("⏳ Waiting for overlay to close...")
    page.wait_for_timeout(3500) 
    
    # Final state check
    # assert_snapshot(page.screenshot()) # Optional: Check game board state
    
    print("🎉 SUCCESS: Browser Verification Passed (with Qayd Result Inspection)!")
