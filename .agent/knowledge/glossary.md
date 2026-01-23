# Baloot Glossary & Code Mapping

A guide to Baloot terminology and its representation in the codebase.

| Term | Meaning | Code Variable / Value | Context |
|---|---|---|---|
| **Sun** | No Trump game mode. A > 10 > K... | `game_mode = "SUN"` | `Game.game_mode` |
| **Hokum** | Trump game mode. J > 9 > A... | `game_mode = "HOKUM"` | `Game.game_mode` |
| **Sawa (Sawa)** | "Complete". Claim to win all remaining tricks. | `Game.handle_sawa()` <br> `Game.sawa_state` | Action & variable |
| **Project (Mashrou)** | Melds (Sequences, 4-of-a-kind) declared for points. | `Game.declarations` <br> `scan_hand_for_projects` | `Game` attribute |
| **Sira** | Sequence of 3 cards. | `{'type': 'SIRA'}` | Project Dictionary |
| **Fifty (Khamsin)** | Sequence of 4 cards. | `{'type': 'FIFTY'}` | Project Dictionary |
| **Hundred (Miah)** | Sequence of 5 cards or 4-of-a-kind (K,Q,J,10). | `{'type': 'HUNDRED'}` | Project Dictionary |
| **Four Hundred** | 4 Aces in Sun. | `{'type': 'FOUR_HUNDRED'}` | Project Dictionary |
| **Baloot** | King + Queen of Trump in Hokum. | `{'type': 'BALOOT'}` | Project Dictionary |
| **Ashkal** | "Forms". Dealer's partner takes the floor card for Sun. | `action="ASHKAL"` | `handle_bid` |
| **Kawesh** | Request redeal (no court cards). | `action="KAWESH"` | `handle_bid` |
| **Qayd** | Penalty / "Bind". Challenging a player's move. | `action="QAYD"` <br> `Game.qayd_state` | Action & variable |
| **Gash** | Redeal (e.g. if everyone passes). | Logic in `handle_bid` (PASS) | -- |
| **Khasara** | Loss. Used when Sawa fails or team fails bid. | `sawa_failed_khasara` | Variable |
| **Kaboot** | Capot. Winning ALL tricks in a round. | Logic in `calculate_score` (implicit) | -- |
