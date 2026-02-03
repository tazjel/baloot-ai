## 2026-02-03 - Accessibility in Custom Components
**Learning:** The app uses a custom `touch-target` class for mobile-friendly sizing but lacks explicit focus states for keyboard users on custom styled buttons.
**Action:** Always verify `focus-visible` styles when encountering custom button components, especially those with non-standard backgrounds (like `bg-white/60`).
