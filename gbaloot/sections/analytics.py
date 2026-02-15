"""
📈 Analytics Section — Cross-session match analytics and trend detection.

Three sub-tabs:
  1. Match Progression — Per-round agreement bar chart
  2. Divergence Heatmap — Mode x trick position divergence density
  3. Trend Summary — Per-mode accuracy breakdown and top patterns
"""
from __future__ import annotations

import streamlit as st
from pathlib import Path

from gbaloot.core.models import ProcessedSession
from gbaloot.core.comparator import GameComparator, ComparisonReport, Divergence
from gbaloot.core.match_analytics import (
    build_match_progression,
    build_divergence_heatmap,
    analyze_trends,
    MatchProgression,
    DivergenceHeatmap,
    TrendAnalysis,
)
from gbaloot.core.session_manifest import (
    load_manifest,
    build_manifest,
    save_manifest,
    get_sessions_by_health,
    HEALTH_ICONS,
)


def render():
    """Main entry point, called from app.py."""
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(126,231,135,0.1) 0%, rgba(22,27,34,0.6) 100%);
        border: 1px solid rgba(126,231,135,0.25); border-radius: 12px; padding: 20px 24px; margin-bottom: 20px;">
        <h2 style="margin:0 0 4px 0; color: #7ee787;">📈 Analytics</h2>
        <p style="margin:0; color: #8b949e; font-size: 0.9rem;">
            Cross-session trends, divergence heatmaps, and per-mode accuracy
        </p>
    </div>""", unsafe_allow_html=True)

    sessions_dir = Path(__file__).resolve().parents[1] / "data" / "sessions"

    manifest = load_manifest(sessions_dir)
    if manifest is None:
        manifest = build_manifest(sessions_dir)
        save_manifest(manifest, sessions_dir)

    good_sessions = get_sessions_by_health(manifest, "good")
    if not good_sessions:
        st.info("No sessions with trick data found. Process and benchmark sessions first.")
        return

    st.caption(f"Found {len(good_sessions)} sessions with trick data")

    # Run comparison on all good sessions
    if st.button("🔄 Analyze All Sessions", type="primary", key="analytics_run"):
        with st.spinner(f"Analyzing {len(good_sessions)} sessions..."):
            reports = _run_all_comparisons(sessions_dir, good_sessions)
            st.session_state["analytics_reports"] = reports
            st.rerun()

    if "analytics_reports" not in st.session_state:
        st.info("Click **Analyze All Sessions** to start.")
        return

    reports = st.session_state["analytics_reports"]
    if not reports:
        st.warning("No comparison reports generated.")
        return

    tab_progression, tab_heatmap, tab_trends = st.tabs([
        "📊 Match Progression", "🔥 Divergence Heatmap", "📋 Trend Summary"
    ])

    with tab_progression:
        _render_progression(reports)
    with tab_heatmap:
        _render_heatmap(reports)
    with tab_trends:
        _render_trends(reports)


def _run_all_comparisons(sessions_dir, good_sessions):
    """Run GameComparator on all good sessions and return reports."""
    reports = []
    for entry in good_sessions:
        path = sessions_dir / entry.filename
        if not path.exists():
            continue
        try:
            session = ProcessedSession.load(path)
            comparator = GameComparator(session.events)
            report = comparator.compare()
            if report and report.trick_comparisons:
                reports.append(report)
        except Exception as e:
            st.warning(f"Failed to analyze {entry.filename}: {e}")
    return reports


def _render_progression(reports):
    """Per-session match progression bar chart."""
    import pandas as pd

    if len(reports) == 1:
        prog = build_match_progression(reports[0])
        st.metric("Overall Agreement", f"{prog.overall_agreement:.1f}%")
        if prog.rounds:
            data = {
                "Round": [f"R{r.round_index}" for r in prog.rounds],
                "Agreement %": [r.agreement_pct for r in prog.rounds],
            }
            df = pd.DataFrame(data).set_index("Round")
            st.bar_chart(df, color="#7ee787")
    else:
        # Multi-session: one bar per session
        data = []
        for i, report in enumerate(reports):
            prog = build_match_progression(report)
            data.append({
                "Session": f"S{i+1}",
                "Agreement %": prog.overall_agreement,
                "Tricks": prog.total_tricks,
            })
        df = pd.DataFrame(data).set_index("Session")
        st.bar_chart(df[["Agreement %"]], color="#7ee787")
        st.dataframe(df, use_container_width=True)


def _divergences_from_reports(reports):
    """Extract Divergence objects from non-agreeing trick comparisons."""
    divs = []
    for report in reports:
        for tc in report.trick_comparisons:
            if not tc.winner_agrees:
                divs.append(Divergence(
                    id=f"div_{len(divs):04d}",
                    session_path=report.session_path,
                    round_index=tc.round_index,
                    trick_number=tc.trick_number,
                    divergence_type=tc.divergence_type or "TRICK_WINNER",
                    severity="HIGH",
                    game_mode=tc.game_mode,
                    trump_suit=tc.trump_suit,
                    cards_played=tc.cards,
                    lead_suit=tc.lead_suit,
                    source_result=f"Seat {tc.source_winner_seat}",
                    engine_result=f"Seat {tc.engine_winner_seat}",
                    notes=tc.notes,
                ))
    return divs


def _render_heatmap(reports):
    """Divergence heatmap across all sessions."""
    all_divergences = _divergences_from_reports(reports)
    all_comparisons = []
    for report in reports:
        all_comparisons.extend(report.trick_comparisons)

    heatmap = build_divergence_heatmap(all_divergences, all_comparisons)

    if not heatmap.cells:
        st.info("No divergences found — 100% agreement!")
        return

    st.caption(f"Modes: {', '.join(heatmap.modes)} | Max trick: {heatmap.max_trick_position}")

    # Build HTML grid
    grid_html = '<div style="display: grid; grid-template-columns: auto ' + ' '.join(
        ['60px'] * heatmap.max_trick_position
    ) + '; gap: 2px; font-size: 0.75rem;">'

    # Header row
    grid_html += '<div style="font-weight: bold; padding: 4px;">Mode</div>'
    for t in range(1, heatmap.max_trick_position + 1):
        grid_html += f'<div style="text-align: center; font-weight: bold; padding: 4px;">T{t}</div>'

    # Build lookup
    cell_lookup = {(c.trick_position, c.mode): c for c in heatmap.cells}

    for mode in heatmap.modes:
        grid_html += f'<div style="font-weight: bold; padding: 4px;">{mode}</div>'
        for t in range(1, heatmap.max_trick_position + 1):
            cell = cell_lookup.get((t, mode))
            if cell and cell.divergence_count > 0:
                intensity = min(cell.divergence_rate, 1.0)
                r = int(248 * intensity)
                g = int(81 * intensity)
                bg = f"rgba({r}, {g}, 73, {0.3 + intensity * 0.7})"
                grid_html += f'<div style="text-align: center; padding: 4px; background: {bg}; border-radius: 4px;">{cell.divergence_count}</div>'
            else:
                grid_html += '<div style="text-align: center; padding: 4px; background: rgba(126,231,135,0.1); border-radius: 4px;">0</div>'

    grid_html += '</div>'
    st.markdown(grid_html, unsafe_allow_html=True)


def _render_trends(reports):
    """Cross-session trend analysis."""
    all_divergences = _divergences_from_reports(reports)
    trends = analyze_trends(reports, all_divergences)

    c1, c2, c3 = st.columns(3)
    c1.metric("Sessions", trends.sessions_analyzed)
    c2.metric("Total Tricks", trends.total_tricks)
    c3.metric("Divergences", trends.total_divergences)

    if trends.per_mode_accuracy:
        st.markdown("##### Per-Mode Accuracy")
        for mode, acc in sorted(trends.per_mode_accuracy.items()):
            count = trends.per_mode_count.get(mode, 0)
            color = "#7ee787" if acc >= 95 else "#f0883e" if acc >= 80 else "#f85149"
            st.markdown(
                f"**{mode}**: <span style='color:{color}'>{acc:.1f}%</span> "
                f"({count} tricks)",
                unsafe_allow_html=True,
            )

    if trends.top_divergence_patterns:
        st.markdown("##### Top Divergence Patterns")
        for pattern, count in trends.top_divergence_patterns[:5]:
            st.caption(f"`{count}x` {pattern}")
