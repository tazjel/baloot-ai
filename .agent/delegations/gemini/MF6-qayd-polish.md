# M-F6: Qayd Dispute System — Antigravity/Gemini Tasks

> **Phase**: M-F6 | **Priority**: After Claude MAX lands core widgets
> **Depends on**: DisputeModal orchestrator + sub-widgets complete

## Task 1: Visual QA — Qayd Dispute Wizard
**Goal**: Verify all 6 steps of the Qayd wizard render correctly and match the React reference.

### Steps
1. Run the Flutter app on a device/emulator
2. Navigate to a game in PLAYING phase
3. Trigger Qayd dispute (tap ⚖️ button in ActionDock)
4. Walk through all 6 steps:
   - MAIN_MENU: 3 buttons (كشف الأوراق, سوا خاطئ, أكة خاطئة) centered
   - VIOLATION_SELECT: Violation type chips (قاطع, ربع في الدبل, etc.)
   - SELECT_CARD_1: Trick gallery with tappable cards, pink ring on selection
   - SELECT_CARD_2: Same gallery, green ring on proof card
   - ADJUDICATION: Loading spinner with "جاري التحقق..."
   - RESULT: Green/Red banner with verdict, evidence cards, penalty
5. Verify timer countdown in footer (60s human, 2s bot)
6. Verify back button navigation works
7. Verify cancel button closes wizard

### Reference
- React implementation: `frontend/src/components/DisputeModal.tsx`
- Sub-components: `frontend/src/components/dispute/`

## Task 2: RTL Layout Verification
**Goal**: Ensure all Arabic text in Qayd widgets renders correctly in RTL.

### Check Points
- [ ] Menu buttons right-to-left order
- [ ] Violation chips right-to-left order
- [ ] Trick cards right-to-left display
- [ ] Reporter badge right-aligned
- [ ] Instruction text right-aligned
- [ ] Verdict banner text right-aligned
- [ ] Back button on left (correct for RTL)

## Task 3: Sawa Modal Polish
**Goal**: Verify the SawaModal at `mobile/lib/widgets/sawa_modal.dart` works correctly.

### Check Points
- [ ] Modal shows when sawa state is active
- [ ] Claimer name displays correctly
- [ ] Response buttons (رفض/موافقة) work
- [ ] Player response status icons update
- [ ] Waiting message shows for claimer
- [ ] Modal auto-closes when resolved

## Task 4: ActionDock Edge Case Buttons
**Goal**: Verify new buttons in PlayingDock render correctly.

### Check Points
- [ ] Sawa button visible during playing phase
- [ ] Qayd button (⚖️) visible during playing phase
- [ ] Akka button only visible in HOKUM when leading
- [ ] Double button label changes: دبل → تربل → كبوت → قهوة
- [ ] Buttons don't overlap or overflow on small screens

## Task 5: Animation Integration
**Goal**: Add step transitions to the Qayd wizard.

### Suggestions
- AnimatedSwitcher between steps (fade + slide)
- Verdict banner spring animation (scaleX 0→1)
- Crime/proof card selection: scale-up + ring animation
- Timer: smooth circular progress with color transition
- Use existing `mobile/lib/animations/ui_animations.dart` patterns

## Files to Review
```
mobile/lib/widgets/dispute/
  qayd_types.dart          — Types & constants
  qayd_main_menu.dart      — 3-button menu
  qayd_card_selector.dart  — Trick browser + card picker
  qayd_verdict_panel.dart  — Verdict display
  qayd_footer.dart         — Timer + reporter
mobile/lib/widgets/dispute_modal.dart — Orchestrator (6-step wizard)
mobile/lib/widgets/sawa_modal.dart    — Sawa tie claim
mobile/lib/widgets/action_dock.dart   — ActionDock with edge case buttons
mobile/lib/screens/game_screen.dart   — Stack with all overlays
```
