---
name: DesignSystem
description: The Design System reference for the Baloot Web App.
---

# DesignSystem Skill

This skill allows you to maintain the "ExternalApp Premium" aesthetic across all UI components. Use these tokens and patterns for any new features.

## Core Tokens (CSS Variables)

Defined in `frontend/index.css`.

### Colors
- **Gold**: `text-[#D4AF37]` (Primary Brand), `bg-[#D4AF37]`
    - Light: `#F4D03F`
    - Dim: `rgba(212, 175, 55, 0.3)`
- **Table Green**: `bg-[#0a5233]` (Rich Felt)
- **Wood Background**: `bg-[#1e110b]`
- **Text**:
    - Main: `#2D3436`
    - Secondary: `#636E72`

### Fonts
- **Headings**: 'Roboto Slab', serif (Latin), 'Cairo', sans-serif (Arabic).
- **Body**: 'Tajawal', sans-serif.

## Components

### Buttons
**Standard Action Button**:
```tsx
<button className="btn-premium-gold">
  Play Now
</button>
```
**Game Action Button** (Pass, Double, etc.):
```tsx
<button className="btn-premium-gold-action bg-zinc-800 text-white hover:bg-zinc-700">
  PASS
</button>
```

### Panels / Modals
**Glass Panel** (Used for Modals, Sidebars):
```tsx
<div className="glass-premium-gold p-6">
  <h2 className="text-[#D4AF37] font-bold text-2xl mb-4">Settings</h2>
  {/* Content */}
</div>
```

### Animations
- **Deal Card**: `animate-deal-card`
- **Play Card**: `animate-throw` (Advanced bezier) or `card-play-out` (Simple)
- **Active Player Ring**: `turn-indicator-active` (Pulse effect)
- **Winner Highlight**: `animate-bounce-subtle`

## Best Practices
1.  **Always use Glassmorphism**: Avoid solid opaque backgrounds for overlays. Use `.glass-premium-gold`.
2.  **Gold Accents**: Use Gold (`#D4AF37`) for critical feedback (Winner, High Score, Trumps).
3.  **Arabic Support**: Use `font-sans` which maps to 'Cairo' to ensure Arabic text renders beautifully.
4.  **Touch Targets**: Ensure buttons are at least `min-w-[48px] min-h-[48px]` for mobile.
