"""
📊 Benchmark Section — Dual-engine comparison between source captures and our
game engine, with divergence tracking, correctness scorecard, and screenshot
correlation.

Five sub-tabs:
  1. Compare — Per-round accordion with bids, tricks, and points unified
  2. Bidding — Bid extraction and comparison for a single session
  3. Divergences — Cross-session edge case collector
  4. Scorecard — Engine correctness badges with G3 point analysis
  5. Screenshots — Screenshot timeline with SSIM scores and event correlation
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
from gbaloot.core.session_manifest import (
    build_manifest,
    save_manifest,
    load_manifest,
    get_entry_by_filename,
    HEALTH_ICONS,
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

    tab_compare, tab_bidding, tab_divergences, tab_scorecard, tab_screenshots = st.tabs([
        "🔬 Compare", "🎯 Bidding", "⚠️ Divergences", "🏆 Scorecard", "📸 Screenshots"
    ])

    with tab_compare:
        _render_compare_tab()
    with tab_bidding:
        _render_bidding_tab()
    with tab_divergences:
        _render_divergences_tab()
    with tab_scorecard:
        _render_scorecard_tab()
    with tab_screenshots:
        _render_screenshots_tab()


# ── Tab 1: Compare (Enhanced with Round Accordion) ─────────────────

def _render_compare_tab():
    """Single-session unified comparison with per-round accordion."""
    sessions_dir = Path(__file__).resolve().parents[1] / "data" / "sessions"
    session_files = sorted(
        sessions_dir.glob("*_processed.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not session_files:
        st.info("No processed sessions found. Use the **Process** tab first.")
        return

    # Load or build manifest for health badges
    manifest = load_manifest(sessions_dir)
    if manifest is None:
        manifest = build_manifest(sessions_dir)
        save_manifest(manifest, sessions_dir)

    def _session_label(name: str) -> str:
        entry = get_entry_by_filename(manifest, name)
        if entry:
            icon = HEALTH_ICONS.get(entry.health, "")
            tricks = f"{entry.trick_count}T" if entry.has_tricks else "0T"
            return f"{icon} {name} ({tricks})"
        return name

    # Controls row
    col_select, col_run, col_manifest = st.columns([3, 1, 1])
    with col_select:
        session_names = [f.name for f in session_files]
        selected = st.selectbox(
            "Select Session",
            session_names,
            format_func=_session_label,
            key="bench_session",
        )
    with col_manifest:
        st.write("")
        if st.button("🔄 Rebuild Manifest", key="bench_rebuild_manifest"):
            manifest = build_manifest(sessions_dir)
            save_manifest(manifest, sessions_dir)
            st.rerun()
    with col_run:
        st.write("")  # Vertical alignment spacer
        run_clicked = st.button(
            "🔬 Run Comparison", type="primary", key="bench_run"
        )

    if run_clicked:
        sel_path = next(f for f in session_files if f.name == selected)
        with st.spinner("Building unified session report..."):
            session = ProcessedSession.load(sel_path)

            # Build unified report (G4)
            try:
                from gbaloot.core.round_report import build_session_report
                session_report = build_session_report(
                    session.events, str(sel_path)
                )
                st.session_state["bench_session_report"] = session_report
                st.session_state["bench_report"] = session_report.comparison_report
                st.session_state["bench_single_divs"] = (
                    GameComparator().compare_session(session.events, str(sel_path)),
                )
            except Exception:
                # Fallback to legacy comparison
                comparator = GameComparator()
                report = comparator.compare_session(session.events, str(sel_path))
                st.session_state["bench_report"] = report
                st.session_state["bench_single_divs"] = comparator.get_divergences()
                st.session_state["bench_session_report"] = None
        st.rerun()

    if "bench_report" not in st.session_state:
        st.caption("Select a session and click **Run Comparison** to begin.")
        return

    report: ComparisonReport = st.session_state["bench_report"]
    session_report = st.session_state.get("bench_session_report")

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

    # View toggle: Round Accordion vs Flat Table
    st.markdown("---")
    view_mode = st.radio(
        "View",
        ["📋 Round Accordion", "📊 Flat Table"],
        horizontal=True,
        key="bench_view_mode",
    )

    if view_mode == "📋 Round Accordion" and session_report:
        _render_round_accordion(session_report)
    else:
        st.markdown("##### Per-Trick Comparison")
        _render_trick_table(report.trick_comparisons)

    # Download buttons
    if session_report:
        st.markdown("---")
        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            from gbaloot.core.report_exporter import session_report_to_dict
            json_data = json.dumps(
                session_report_to_dict(session_report),
                indent=2, ensure_ascii=False,
            )
            st.download_button(
                "📥 Download Report (JSON)",
                json_data,
                file_name="session_report.json",
                mime="application/json",
                key="bench_dl_json",
            )
        with dl_col2:
            from gbaloot.core.report_exporter import session_report_to_markdown
            md_data = session_report_to_markdown(session_report)
            st.download_button(
                "📥 Download Report (MD)",
                md_data,
                file_name="session_report.md",
                mime="text/markdown",
                key="bench_dl_md",
            )

    # Extraction warnings
    if report.extraction_warnings:
        with st.expander(
            f"⚠️ {len(report.extraction_warnings)} extraction warnings"
        ):
            for w in report.extraction_warnings:
                st.caption(w)


def _render_round_accordion(session_report):
    """Render unified per-round accordion with bids, tricks, and points."""
    from gbaloot.core.round_report import SessionReport, RoundReport

    if not session_report.rounds:
        st.caption("No rounds to display.")
        return

    # Session-level summary
    col1, col2, col3 = st.columns(3)
    col1.metric("Rounds with Bids", session_report.rounds_with_bids)
    col2.metric("Complete Rounds", session_report.complete_rounds)
    col3.metric("Point-Consistent", session_report.point_consistent_rounds)

    st.markdown("")

    for rr in session_report.rounds:
        # Build accordion label
        mode_icon = "☀️" if rr.game_mode == "SUN" else "🃏"
        trump_str = f" {rr.trump_suit}" if rr.trump_suit else ""
        status = rr.overall_status
        bid_tag = " 🎯" if rr.has_bidding else ""
        pts_tag = " 📐" if rr.has_points else ""

        label = (
            f"{status} Round {rr.round_index + 1}: "
            f"{mode_icon} {rr.game_mode}{trump_str} — "
            f"{rr.num_tricks} tricks, {rr.trick_agreement_pct:.0f}% agree"
            f"{bid_tag}{pts_tag}"
        )

        with st.expander(label):
            _render_round_detail(rr)


def _render_round_detail(rr):
    """Render the interior of one round accordion."""
    # ── Bidding section ──
    if rr.has_bidding:
        st.markdown("**🎯 Bidding**")
        seq = rr.bid_sequence
        caller_str = f"Caller: Seat {seq.caller_seat}" if seq.caller_seat >= 0 else ""
        dealer_str = f"Dealer: Seat {seq.dealer_seat}" if seq.dealer_seat >= 0 else ""
        st.caption(f"{dealer_str} | {caller_str} | {len(seq.bids)} bids")
        for bid in seq.bids:
            icon = "🚫" if bid.action == "PASS" else "☀️" if bid.action == "SUN" else "🃏"
            st.caption(
                f"  `Seat {bid.seat}` {icon} **{bid.action}** (round {bid.bidding_round})"
            )
        st.markdown("")

    # ── Tricks section ──
    if rr.trick_comparisons:
        st.markdown("**🃏 Tricks**")
        import pandas as pd

        rows = []
        for tc in rr.trick_comparisons:
            cards_str = ", ".join(f"{c['card']}" for c in tc.cards)
            status = "✅" if tc.winner_agrees else "❌"
            rows.append({
                "Trick": tc.trick_number,
                "Cards": cards_str,
                "Lead": tc.lead_suit,
                "Src": f"S{tc.source_winner_seat}",
                "Eng": f"S{tc.engine_winner_seat}",
                "Pts": tc.engine_points,
                "": status,
            })

        df = pd.DataFrame(rows)

        def _color_row(row):
            if row[""] == "❌":
                return ["background-color: rgba(248,81,73,0.15)"] * len(row)
            return [""] * len(row)

        styled = df.style.apply(_color_row, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True, height=min(len(rows) * 38 + 40, 350))

    # ── Points section ──
    if rr.has_points:
        pa = rr.point_analysis
        st.markdown("**📐 Points**")
        p_cols = st.columns(4)
        p_cols[0].caption(f"Team 0+2: {pa.raw_abnat_team_02} raw")
        p_cols[1].caption(f"Team 1+3: {pa.raw_abnat_team_13} raw")
        if pa.is_complete_round:
            p_cols[2].caption(f"GP: {pa.gp_team_02} vs {pa.gp_team_13}")
            consistency_icon = "✅" if pa.card_points_consistent else "❌"
            p_cols[3].caption(f"Consistent: {consistency_icon}")
        if pa.last_trick_team:
            st.caption(f"Last trick bonus → {pa.last_trick_team}")
        if pa.notes:
            st.caption(f"⚠️ {pa.notes}")


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


# ── Tab 2: Bidding ─────────────────────────────────────────────────

def _render_bidding_tab():
    """Bidding extraction and comparison for a single session."""
    sessions_dir = Path(__file__).resolve().parents[1] / "data" / "sessions"
    session_files = sorted(
        sessions_dir.glob("*_processed.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not session_files:
        st.info("No processed sessions found. Use the **Process** tab first.")
        return

    col_select, col_run = st.columns([3, 1])
    with col_select:
        selected = st.selectbox(
            "Select Session",
            [f.name for f in session_files],
            key="bid_session",
        )
    with col_run:
        st.write("")
        run_clicked = st.button(
            "🎯 Extract Bids", type="primary", key="bid_run"
        )

    if run_clicked:
        sel_path = next(f for f in session_files if f.name == selected)
        with st.spinner("Extracting bidding sequences..."):
            try:
                from gbaloot.core.bid_extractor import extract_bids
                session = ProcessedSession.load(sel_path)
                bid_result = extract_bids(session.events, str(sel_path))
                st.session_state["bid_result"] = bid_result
            except Exception as e:
                st.error(f"Bid extraction failed: {e}")
                return
        st.rerun()

    if "bid_result" not in st.session_state:
        st.caption("Select a session and click **Extract Bids** to analyze bidding.")
        return

    from gbaloot.core.bid_extractor import BidExtractionResult, ExtractedBidSequence
    bid_result: BidExtractionResult = st.session_state["bid_result"]

    if not bid_result.sequences:
        st.warning("No bidding sequences found in this session.")
        return

    # Summary metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Bidding Rounds", len(bid_result.sequences))
    c2.metric("Total Bids", bid_result.total_bids)
    c3.metric("Events Scanned", bid_result.total_events_scanned)

    # Per-sequence display
    st.markdown("---")
    st.markdown("##### Bidding Sequences")

    for seq in bid_result.sequences:
        mode_icon = "☀️" if seq.final_mode == "SUN" else "🃏" if seq.final_mode == "HOKUM" else "⏭️"
        trump_str = ""
        if seq.final_trump_idx is not None:
            from gbaloot.core.card_mapping import suit_idx_to_symbol
            trump_str = f" Trump: {suit_idx_to_symbol(seq.final_trump_idx)}"
        caller_str = f" (Seat {seq.caller_seat})" if seq.caller_seat >= 0 else ""

        with st.expander(
            f"{mode_icon} Round {seq.round_index + 1}: "
            f"{seq.final_mode or 'ALL PASS'}{trump_str}{caller_str} "
            f"— {len(seq.bids)} bids"
        ):
            for bid in seq.bids:
                icon = "🚫" if bid.action == "PASS" else "☀️" if bid.action == "SUN" else "🃏"
                st.caption(
                    f"`Seat {bid.seat}` {icon} **{bid.action}** "
                    f"(raw: {bid.raw_bt}, round {bid.bidding_round})"
                )


# ── Tab 3: Divergences ──────────────────────────────────────────────

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


# ── Tab 4: Scorecard ────────────────────────────────────────────────

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

    # Download scorecard
    scorecard_json = json.dumps(scorecard, indent=2, ensure_ascii=False)
    st.download_button(
        "📥 Download Scorecard (JSON)",
        scorecard_json,
        file_name="scorecard.json",
        mime="application/json",
        key="bench_dl_scorecard",
    )

    # G3: Point analysis summary (if available)
    has_points = any(report.point_analyses for report in reports)
    if has_points:
        st.markdown("---")
        st.markdown("##### 📐 Point Analysis (G3)")
        all_pa = []
        for r in reports:
            all_pa.extend(r.point_analyses)
        complete = [pa for pa in all_pa if pa.is_complete_round]
        if complete:
            consistent = sum(1 for pa in complete if pa.card_points_consistent)
            gp_ok = sum(1 for pa in complete if pa.gp_sum_matches_target)
            st.caption(
                f"{len(complete)} complete rounds analyzed · "
                f"Card points consistent: {consistent}/{len(complete)} · "
                f"GP sum matches target: {gp_ok}/{len(complete)}"
            )
        else:
            st.caption("No complete 8-trick rounds found for point analysis.")


# ── Tab 5: Screenshots ──────────────────────────────────────────────

def _render_screenshots_tab():
    """Screenshot timeline with SSIM scores and event correlation."""
    screenshots_base = Path(__file__).resolve().parents[1] / "data" / "captures" / "screenshots"

    if not screenshots_base.exists():
        st.info(
            "No screenshots directory found. Screenshots are captured during "
            "live game recording via the **Capture** tab."
        )
        st.caption(f"Expected path: `{screenshots_base}`")
        return

    # List available session screenshot directories
    session_dirs = sorted(
        [d for d in screenshots_base.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )

    if not session_dirs:
        st.info(
            "No screenshot sessions found. Run a live capture with screenshots enabled."
        )
        st.caption(
            "Use: `python gbaloot/capture_session.py --label my_game --screenshots`"
        )
        return

    # Session picker
    col_select, col_run = st.columns([3, 1])
    with col_select:
        selected_dir = st.selectbox(
            "Screenshot Session",
            [d.name for d in session_dirs],
            key="ss_session",
        )
    with col_run:
        st.write("")
        run_clicked = st.button(
            "📸 Analyze", type="primary", key="ss_run"
        )

    if run_clicked:
        ss_dir = screenshots_base / selected_dir
        screenshots = sorted(ss_dir.glob("*.png"))

        if len(screenshots) < 2:
            st.warning(f"Need at least 2 screenshots (found {len(screenshots)}).")
            return

        with st.spinner(f"Comparing {len(screenshots)} screenshots..."):
            try:
                from gbaloot.tools.screenshot_diff import (
                    compare_session_screenshots,
                    generate_diff_report,
                )
                results = compare_session_screenshots(selected_dir)
                if results:
                    generate_diff_report(selected_dir, results)
                st.session_state["ss_results"] = results
                st.session_state["ss_dir"] = str(ss_dir)
                st.session_state["ss_count"] = len(screenshots)
            except Exception as e:
                st.error(f"Screenshot analysis failed: {e}")
                return
        st.rerun()

    if "ss_results" not in st.session_state:
        st.caption("Select a screenshot session and click **Analyze** to begin.")
        return

    results = st.session_state["ss_results"]
    ss_dir = st.session_state.get("ss_dir", "")
    ss_count = st.session_state.get("ss_count", 0)

    if not results:
        st.warning("No comparison results available.")
        return

    # Summary metrics
    avg_sim = sum(r.get("similarity_pct", 0) for r in results) / len(results)
    big_changes = [r for r in results if r.get("similarity_pct", 100) < 85]

    c1, c2, c3 = st.columns(3)
    c1.metric("Screenshots", ss_count)
    c2.metric("Avg Similarity", f"{avg_sim:.1f}%")
    c3.metric("Big Changes", len(big_changes))

    # Timeline
    st.markdown("---")
    st.markdown("##### Screenshot Transition Timeline")

    for r in results:
        similarity = r.get("similarity_pct", 0)
        method = r.get("method", "pixel")
        transition = r.get("transition", f"Frame {r.get('index', '?')}")
        indicator = "🟢" if similarity > 95 else "🟡" if similarity > 80 else "🔴"

        col_icon, col_info, col_sim = st.columns([0.5, 4, 1])
        with col_icon:
            st.markdown(indicator)
        with col_info:
            st.caption(transition)
        with col_sim:
            st.caption(f"{similarity:.1f}%")

    # Significant transitions detail
    if big_changes:
        st.markdown("---")
        st.markdown("##### Significant State Transitions")
        for r in big_changes:
            with st.expander(
                f"🔴 {r.get('transition', '?')} — {r.get('similarity_pct', 0):.1f}% similar"
            ):
                st.caption(f"Method: {r.get('method', 'pixel')}")
                st.caption(f"Image A: {r.get('image_a', '?')}")
                st.caption(f"Image B: {r.get('image_b', '?')}")
                if r.get("diff_image"):
                    try:
                        st.image(r["diff_image"], caption="Difference overlay")
                    except Exception:
                        st.caption(f"Diff image: {r['diff_image']}")


# ── Shared Helper ────────────────────────────────────────────────────

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
