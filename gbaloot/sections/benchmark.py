"""
📊 Benchmark Section — Dual-engine comparison between source captures and our
game engine, with divergence tracking and correctness scorecard.
"""
from __future__ import annotations

import json
import streamlit as st
from pathlib import Path

from gbaloot.core.models import ProcessedSession
from gbaloot.core.comparator import (
    GameComparator,
    ComparisonReport,
    TrickComparison,
    Divergence,
    generate_scorecard,
)


def render():
    """Main entry point, called from app.py."""
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(240,136,62,0.1) 0%, rgba(22,27,34,0.6) 100%);
        border: 1px solid rgba(240,136,62,0.25); border-radius: 12px; padding: 20px 24px; margin-bottom: 20px;">
        <h2 style="margin:0 0 4px 0; color: #f0883e;">📊 Benchmark</h2>
        <p style="margin:0; color: #8b949e; font-size: 0.9rem;">
            Compare source vs. our engine — trick resolution, point calculation, divergence tracking
        </p>
    </div>""", unsafe_allow_html=True)

    tab_compare, tab_divergences, tab_scorecard = st.tabs([
        "🔬 Compare", "⚠️ Divergences", "🏆 Scorecard"
    ])

    with tab_compare:
        _render_compare_tab()
    with tab_divergences:
        _render_divergences_tab()
    with tab_scorecard:
        _render_scorecard_tab()


# ── Tab 1: Compare ──────────────────────────────────────────────────

def _render_compare_tab():
    """Single-session comparison workflow."""
    sessions_dir = Path(__file__).resolve().parents[1] / "data" / "sessions"
    session_files = sorted(
        sessions_dir.glob("*_processed.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not session_files:
        st.info("No processed sessions found. Use the **Process** tab first.")
        return

    # Controls row
    col_select, col_run = st.columns([3, 1])
    with col_select:
        selected = st.selectbox(
            "Select Session",
            [f.name for f in session_files],
            key="bench_session",
        )
    with col_run:
        st.write("")  # Vertical alignment spacer
        run_clicked = st.button(
            "🔬 Run Comparison", type="primary", key="bench_run"
        )

    if run_clicked:
        sel_path = next(f for f in session_files if f.name == selected)
        with st.spinner("Comparing engines..."):
            session = ProcessedSession.load(sel_path)
            comparator = GameComparator()
            report = comparator.compare_session(session.events, str(sel_path))
            st.session_state["bench_report"] = report
            st.session_state["bench_single_divs"] = comparator.get_divergences()
        st.rerun()

    if "bench_report" not in st.session_state:
        st.caption("Select a session and click **Run Comparison** to begin.")
        return

    report: ComparisonReport = st.session_state["bench_report"]

    if report.total_tricks == 0:
        st.warning("No tricks found in this session. Try a session with gameplay data.")
        return

    # Summary metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tricks Compared", report.total_tricks)
    c2.metric("Agreement", f"{report.winner_agreement_pct:.1f}%")
    c3.metric(
        "Divergences",
        report.total_divergences,
        delta=f"-{report.total_divergences}" if report.total_divergences else "0",
        delta_color="inverse",
    )
    c4.metric("Rounds", report.rounds_compared)

    # Per-trick table
    st.markdown("---")
    st.markdown("##### Per-Trick Comparison")
    _render_trick_table(report.trick_comparisons)

    # Extraction warnings
    if report.extraction_warnings:
        with st.expander(
            f"⚠️ {len(report.extraction_warnings)} extraction warnings"
        ):
            for w in report.extraction_warnings:
                st.caption(w)


def _render_trick_table(comparisons: list[TrickComparison]):
    """Render comparison results as a color-coded table."""
    import pandas as pd

    rows = []
    for tc in comparisons:
        cards_str = ", ".join(
            f"{c['card']}" for c in tc.cards
        )
        status = "✅" if tc.winner_agrees else "❌"
        rows.append({
            "Round": tc.round_index + 1,
            "Trick": tc.trick_number,
            "Cards": cards_str,
            "Mode": tc.game_mode,
            "Lead": tc.lead_suit,
            "K.Winner": f"Seat {tc.source_winner_seat}",
            "E.Winner": f"Seat {tc.engine_winner_seat}",
            "Points": tc.engine_points,
            "Status": status,
        })

    df = pd.DataFrame(rows)

    # Style: red background for divergences
    def _color_row(row):
        if row["Status"] == "❌":
            return ["background-color: rgba(248,81,73,0.15)"] * len(row)
        return [""] * len(row)

    styled = df.style.apply(_color_row, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)


# ── Tab 2: Divergences ──────────────────────────────────────────────

def _render_divergences_tab():
    """Cross-session edge case collector."""
    sessions_dir = Path(__file__).resolve().parents[1] / "data" / "sessions"

    col_run, col_info = st.columns([1, 2])
    with col_run:
        if st.button(
            "🔍 Analyze All Sessions", type="primary", key="bench_all"
        ):
            with st.spinner("Analyzing all sessions..."):
                session_files = sorted(sessions_dir.glob("*_processed.json"))
                comparator = GameComparator()
                reports: list[ComparisonReport] = []
                progress = st.progress(0)
                for i, f in enumerate(session_files):
                    try:
                        session = ProcessedSession.load(f)
                        report = comparator.compare_session(
                            session.events, str(f)
                        )
                        reports.append(report)
                    except Exception:
                        pass  # Skip broken sessions
                    progress.progress((i + 1) / max(len(session_files), 1))
                st.session_state["bench_all_reports"] = reports
                st.session_state["bench_all_divergences"] = (
                    comparator.get_divergences()
                )
            st.rerun()

    if "bench_all_divergences" not in st.session_state:
        with col_info:
            st.caption("Click **Analyze All Sessions** to scan for divergences.")
        return

    divergences: list[Divergence] = st.session_state["bench_all_divergences"]
    reports: list[ComparisonReport] = st.session_state["bench_all_reports"]
    total_tricks = sum(r.total_tricks for r in reports)

    with col_info:
        st.caption(
            f"{len(reports)} sessions, {total_tricks} tricks, "
            f"{len(divergences)} divergences"
        )

    if not divergences:
        st.success("🎉 No divergences found! Engines are in perfect agreement.")
        return

    # Filters
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        all_types = sorted(set(d.divergence_type for d in divergences))
        type_filter = st.selectbox(
            "Divergence Type",
            ["All"] + all_types,
            key="bench_div_type",
        )
    with col_f2:
        severity_filter = st.selectbox(
            "Severity",
            ["All", "HIGH", "MEDIUM", "LOW"],
            key="bench_div_sev",
        )

    filtered = divergences
    if type_filter != "All":
        filtered = [d for d in filtered if d.divergence_type == type_filter]
    if severity_filter != "All":
        filtered = [d for d in filtered if d.severity == severity_filter]

    st.caption(f"Showing {len(filtered)} of {len(divergences)} divergences")

    # Divergence list
    for div in filtered:
        session_name = (
            Path(div.session_path).stem if div.session_path else "?"
        )
        sev_icon = (
            "🔴" if div.severity == "HIGH"
            else "🟡" if div.severity == "MEDIUM"
            else "🟢"
        )
        with st.expander(
            f"{sev_icon} R{div.round_index + 1}T{div.trick_number} | "
            f"{div.divergence_type} | {div.game_mode} | {session_name}"
        ):
            st.markdown(f"**Source**: {div.source_result}")
            st.markdown(f"**Engine**: {div.engine_result}")
            cards_str = ", ".join(
                f"Seat {c['seat']}: {c['card']}" for c in div.cards_played
            )
            st.markdown(f"**Cards**: {cards_str}")
            st.markdown(f"**Lead suit**: {div.lead_suit}")
            if div.trump_suit:
                st.markdown(f"**Trump**: {div.trump_suit}")
            if div.notes:
                st.caption(div.notes)

    # Export
    if filtered:
        export_data = json.dumps(
            [d.to_dict() for d in filtered],
            indent=2,
            ensure_ascii=False,
        )
        st.download_button(
            "📥 Export Divergences (JSON)",
            export_data,
            file_name="divergences.json",
            mime="application/json",
            key="bench_download",
        )


# ── Tab 3: Scorecard ────────────────────────────────────────────────

def _render_scorecard_tab():
    """Engine correctness scorecard with badge display."""
    if "bench_all_reports" not in st.session_state:
        st.info(
            "Run **Analyze All Sessions** in the Divergences tab first."
        )
        return

    reports: list[ComparisonReport] = st.session_state["bench_all_reports"]
    scorecard = generate_scorecard(reports)

    st.markdown("##### Engine Correctness Scorecard")
    st.caption(
        f"{scorecard['sessions_analyzed']} sessions, "
        f"{scorecard['total_tricks']} tricks analyzed"
    )

    # Badge grid (2x2)
    col1, col2 = st.columns(2)
    with col1:
        info = scorecard["trick_resolution"]
        _render_badge(
            "Trick Resolution",
            info["agreement_pct"],
            info["total"],
            info["correct"],
        )
    with col2:
        info = scorecard["point_calculation"]
        _render_badge(
            "Point Calculation",
            info["agreement_pct"],
            info["total"],
            info["correct"],
        )

    st.markdown("")  # Spacer

    col3, col4 = st.columns(2)
    with col3:
        info = scorecard["sun_mode"]
        _render_badge(
            "SUN Mode",
            info["agreement_pct"],
            info["total"],
            info["correct"],
        )
    with col4:
        info = scorecard["hokum_mode"]
        _render_badge(
            "HOKUM Mode",
            info["agreement_pct"],
            info["total"],
            info["correct"],
        )

    # Overall badge (full width)
    st.markdown("---")
    info = scorecard["overall"]
    _render_badge(
        "Overall Engine Correctness",
        info["agreement_pct"],
        info["total"],
        info["correct"],
    )


def _render_badge(label: str, pct: float, total: int, correct: int):
    """Render a colored confidence badge.

    @param label: Category name.
    @param pct: Agreement percentage (0-100).
    @param total: Total items checked.
    @param correct: Number of correct items.
    """
    if pct >= 95:
        color = "#7ee787"
        bg = "rgba(126,231,135,0.1)"
        icon = "🟢"
    elif pct >= 80:
        color = "#d29922"
        bg = "rgba(210,153,34,0.1)"
        icon = "🟡"
    else:
        color = "#f85149"
        bg = "rgba(248,81,73,0.1)"
        icon = "🔴"

    tricks_text = f"{correct} / {total} tricks" if total > 0 else "No data"

    st.markdown(f"""
    <div style="background: {bg}; border: 2px solid {color};
        border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 12px;">
        <div style="font-size: 2.2rem; font-weight: 700; color: {color};">
            {icon} {pct:.1f}%
        </div>
        <div style="font-size: 0.95rem; color: #c9d1d9; margin-top: 6px; font-weight: 500;">
            {label}
        </div>
        <div style="font-size: 0.8rem; color: #8b949e; margin-top: 2px;">
            {tricks_text}
        </div>
    </div>""", unsafe_allow_html=True)
