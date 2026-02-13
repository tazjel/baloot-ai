"""
🧪 Test Manager — Streamlit Dashboard Module (v2: Test Intelligence Center)

Run, explore, and track pytest results with coverage heatmap,
slow test detection, parallel execution, and flaky test tracking.

Tools used:
  - pytest-json-report  (structured results)
  - pytest-cov          (coverage heatmap)
  - pytest-xdist        (parallel execution)
  - pytest-rerunfailures (flaky detection)
"""
import streamlit as st
import subprocess
import json
import os
from datetime import datetime
from pathlib import Path

# --- Constants ---
PROJECT_ROOT = Path(__file__).resolve().parents[3]
TESTS_DIR = PROJECT_ROOT / "tests"
DASHBOARD_DIR = Path(__file__).parent.parent
HISTORY_FILE = DASHBOARD_DIR / "test_history.json"
REPORT_FILE = PROJECT_ROOT / ".test_report.json"
COVERAGE_JSON = PROJECT_ROOT / "coverage.json"

# Source directories to track coverage for
COV_SOURCES = ["game_engine", "server", "ai_worker"]

TEST_MODULES = {
    "game_logic": "🎮", "features": "🧩", "bot": "🤖",
    "bidding": "🃏", "ai_features": "🧠", "server": "🌐",
    "browser": "🌍", "qayd": "⚖️", "unit": "🔬", "root": "📁",
}

# Thresholds
SLOW_THRESHOLD_WARN = 1.0   # seconds — yellow
SLOW_THRESHOLD_CRIT = 3.0   # seconds — red
COV_GOOD = 80
COV_WARN = 50


# =============================================================================
#  HELPERS
# =============================================================================

def _discover_tests():
    """Discover all test files grouped by module."""
    modules = {}
    if not TESTS_DIR.exists():
        return modules
    for f in sorted(TESTS_DIR.rglob("test_*.py")):
        rel = f.relative_to(TESTS_DIR)
        mod = rel.parts[0] if len(rel.parts) > 1 else "root"
        modules.setdefault(mod, []).append({
            "name": f.stem,
            "path": str(f.relative_to(PROJECT_ROOT)),
            "size_kb": round(f.stat().st_size / 1024, 1),
        })
    return modules


def _run_pytest(target="tests/", extra_args=None, with_coverage=False):
    """Run pytest and return structured results."""
    report_path = str(REPORT_FILE)
    cmd = [
        "python", "-m", "pytest", target,
        "--json-report", f"--json-report-file={report_path}",
        "--tb=short", "-q", "--no-header",
    ]
    if with_coverage:
        for src in COV_SOURCES:
            src_path = PROJECT_ROOT / src
            if src_path.exists():
                cmd.append(f"--cov={src}")
        cmd.extend([
            f"--cov-report=json:{COVERAGE_JSON}",
            "--cov-report=",  # suppress terminal output
        ])
    if extra_args:
        cmd.extend(extra_args)

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(PROJECT_ROOT), timeout=300,
        )
        report = None
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as fh:
                report = json.load(fh)
        coverage = None
        if with_coverage and COVERAGE_JSON.exists():
            try:
                with open(str(COVERAGE_JSON), "r", encoding="utf-8") as fh:
                    coverage = json.load(fh)
            except Exception:
                pass
        return {
            "success": True, "report": report, "coverage": coverage,
            "stdout": result.stdout, "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Test run timed out (300s limit)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _parse_summary(report):
    if not report:
        return None
    s = report.get("summary", {})
    return {
        "total": s.get("total", 0), "passed": s.get("passed", 0),
        "failed": s.get("failed", 0), "skipped": s.get("skipped", 0),
        "errors": s.get("error", 0),
        "duration": round(report.get("duration", 0), 2),
    }


def _parse_coverage(cov_json):
    """Parse coverage.json into per-module percentages."""
    if not cov_json:
        return None, 0
    totals = cov_json.get("totals", {})
    overall = round(totals.get("percent_covered", 0), 1)

    modules = {}
    for filepath, data in cov_json.get("files", {}).items():
        # Group by top-level source dir
        parts = Path(filepath).parts
        if parts:
            mod = parts[0]
            if mod in COV_SOURCES:
                if mod not in modules:
                    modules[mod] = {"stmts": 0, "miss": 0}
                summary = data.get("summary", {})
                modules[mod]["stmts"] += summary.get("num_statements", 0)
                modules[mod]["miss"] += summary.get("missing_lines", 0)

    for mod, d in modules.items():
        d["pct"] = round((1 - d["miss"] / max(d["stmts"], 1)) * 100, 1)

    return modules, overall


def _get_slow_tests(report, limit=10):
    """Get slowest tests from report."""
    if not report:
        return []
    tests = []
    for t in report.get("tests", []):
        dur = t.get("duration", 0)
        if dur > 0:
            tests.append({
                "nodeid": t.get("nodeid", ""),
                "duration": round(dur, 3),
                "outcome": t.get("outcome", ""),
            })
    tests.sort(key=lambda x: x["duration"], reverse=True)
    return tests[:limit]


def _get_failed_tests(report):
    if not report:
        return []
    return [
        {
            "nodeid": t.get("nodeid", ""),
            "duration": round(t.get("duration", 0), 3),
            "message": t.get("call", {}).get("longrepr", "")[:500],
        }
        for t in report.get("tests", []) if t.get("outcome") == "failed"
    ]


def _get_test_breakdown(report):
    if not report:
        return {}
    files = {}
    for t in report.get("tests", []):
        nid = t.get("nodeid", "")
        fp = nid.split("::")[0] if "::" in nid else nid
        files.setdefault(fp, {"passed": 0, "failed": 0, "skipped": 0, "total": 0})
        files[fp]["total"] += 1
        out = t.get("outcome", "")
        if out in files[fp]:
            files[fp][out] += 1
    return files


def _detect_flaky(history, threshold=3):
    """Detect potential flaky tests by analyzing pass/fail oscillation in history.
    If a test goes from pass→fail or fail→pass more than threshold times, it's flaky."""
    if len(history) < 3:
        return []
    # Simple heuristic: check if pass rate oscillates between runs
    flaky_signals = []
    for i in range(1, len(history)):
        prev = history[i - 1]
        curr = history[i]
        if prev.get("passed", 0) > 0 and curr.get("failed", 0) > 0:
            if prev.get("failed", 0) == 0:  # was green, now red
                flaky_signals.append({"run": i + 1, "change": "🟢→🔴", "ts": curr.get("timestamp", "")})
        elif prev.get("failed", 0) > 0 and curr.get("failed", 0) == 0:
            flaky_signals.append({"run": i + 1, "change": "🔴→🟢", "ts": curr.get("timestamp", "")})
    return flaky_signals


def _save_history(summary, coverage_pct=None):
    history = _load_history()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "total": summary["total"], "passed": summary["passed"],
        "failed": summary["failed"], "skipped": summary["skipped"],
        "duration": summary["duration"],
    }
    if coverage_pct is not None:
        entry["coverage"] = coverage_pct
    history.append(entry)
    history = history[-50:]
    with open(str(HISTORY_FILE), "w", encoding="utf-8") as fh:
        json.dump(history, fh, indent=2)


def _load_history():
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(str(HISTORY_FILE), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return []


# =============================================================================
#  RENDER SECTIONS
# =============================================================================

def _render_health_bar(summary, coverage_pct=None):
    """Top-level health metrics bar."""
    cols = st.columns(6 if coverage_pct is not None else 5)
    rate = round(summary["passed"] / max(summary["total"], 1) * 100, 1)
    cols[0].metric("📊 Total", summary["total"])
    cols[1].metric("✅ Pass Rate", f"{rate}%")
    cols[2].metric("❌ Failures", summary["failed"])
    cols[3].metric("⏱️ Duration", f"{summary['duration']}s")
    cols[4].metric("⏭️ Skipped", summary["skipped"])
    if coverage_pct is not None:
        cols[5].metric("🛡️ Coverage", f"{coverage_pct}%")


def _render_coverage_heatmap(cov_modules):
    """Color-coded coverage bars per source module."""
    st.subheader("🛡️ Code Coverage")
    if not cov_modules:
        st.info("Enable **📊 With Coverage** and run tests to see coverage data.")
        return

    for mod, data in sorted(cov_modules.items()):
        pct = data["pct"]
        stmts = data["stmts"]
        miss = data["miss"]

        if pct >= COV_GOOD:
            color = "#22c55e"  # green
            icon = "🟢"
        elif pct >= COV_WARN:
            color = "#eab308"  # yellow
            icon = "🟡"
        else:
            color = "#ef4444"  # red
            icon = "🔴"

        st.markdown(f"""
        <div style="margin-bottom: 8px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:2px;">
                <span>{icon} <b>{mod}</b></span>
                <span>{pct}% ({stmts - miss}/{stmts} stmts)</span>
            </div>
            <div style="background:#333; border-radius:4px; height:12px; overflow:hidden;">
                <div style="width:{min(pct, 100)}%; background:{color}; height:100%; border-radius:4px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _render_slow_tests(report):
    """Highlight slowest tests after a run."""
    st.subheader("🐌 Slow Tests")
    slow = _get_slow_tests(report)
    if not slow:
        st.success("No slow tests detected!")
        return

    has_slow = any(t["duration"] >= SLOW_THRESHOLD_WARN for t in slow)
    if not has_slow:
        st.success("All tests are fast! ⚡")
        return

    rows = []
    for t in slow:
        if t["duration"] >= SLOW_THRESHOLD_CRIT:
            severity = "🔴 Critical"
        elif t["duration"] >= SLOW_THRESHOLD_WARN:
            severity = "🟡 Slow"
        else:
            severity = "🟢 Fast"
        rows.append({
            "Severity": severity,
            "Test": t["nodeid"],
            "Duration": f"{t['duration']}s",
            "Result": "✅" if t["outcome"] == "passed" else "❌",
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_flaky_tracker(history):
    """Detect test suite stability oscillations."""
    st.subheader("🔄 Stability Tracker")
    if len(history) < 3:
        st.info("Need at least 3 test runs to detect flaky patterns.")
        return

    signals = _detect_flaky(history)
    if not signals:
        st.success("✨ No flaky signals! Test suite is stable across runs.")
    else:
        st.warning(f"⚠️ Found {len(signals)} stability oscillation(s) in recent history")
        for sig in signals[-5:]:  # Show last 5
            st.markdown(f"- Run #{sig['run']}: {sig['change']} at `{sig['ts'][:19]}`")


# =============================================================================
#  MAIN RENDER
# =============================================================================

def render_test_manager_tab():
    """Main entry point for the Test Manager tab."""
    try:
        st.header("🧪 Test Manager")
        st.caption("Run, explore, and track your test suite — powered by pytest-cov, xdist, and rerunfailures.")

        # ── Health Summary ──────────────────────────────────
        last_summary = st.session_state.get("tm_last_summary")
        last_cov_pct = st.session_state.get("tm_last_cov_pct")
        if last_summary:
            _render_health_bar(last_summary, last_cov_pct)
        else:
            st.info("No test data yet. Click **▶️ Run Tests** below to get started.")

        st.markdown("---")

        # ── Run Controls ────────────────────────────────────
        st.subheader("▶️ Run Controls")

        modules = _discover_tests()
        module_options = ["All Tests"] + sorted(modules.keys())

        col1, col2 = st.columns([3, 1])
        with col1:
            selected = st.selectbox(
                "Test scope", module_options,
                format_func=lambda m: "🏠 All Tests" if m == "All Tests"
                    else f"{TEST_MODULES.get(m, '📁')} {m} ({len(modules.get(m, []))} files)",
                key="tm_scope",
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            run_clicked = st.button("▶️ Run Tests", type="primary", use_container_width=True, key="tm_run")

        # Options row
        oc1, oc2, oc3, oc4, oc5 = st.columns(5)
        verbose    = oc1.checkbox("Verbose (-v)", key="tm_verbose")
        fail_fast  = oc2.checkbox("Stop on fail (-x)", key="tm_failfast")
        last_fail  = oc3.checkbox("Rerun failed (--lf)", key="tm_lastfail")
        parallel   = oc4.checkbox("⚡ Parallel", key="tm_parallel")
        with_cov   = oc5.checkbox("📊 Coverage", key="tm_coverage", value=True)

        if run_clicked:
            target = "tests/" if selected == "All Tests" else f"tests/{selected}/"
            extra = []
            if verbose:   extra.append("-v")
            if fail_fast: extra.append("-x")
            if last_fail: extra.append("--lf")
            if parallel:  extra.extend(["-n", "auto"])

            with st.spinner(f"🧪 Running: `{target}`{'  ⚡ parallel' if parallel else ''}{'  📊 +coverage' if with_cov else ''}..."):
                result = _run_pytest(target, extra, with_coverage=with_cov)

            if result["success"]:
                report = result.get("report")
                summary = _parse_summary(report)
                if summary:
                    # Parse coverage
                    cov_modules, cov_overall = _parse_coverage(result.get("coverage"))
                    _save_history(summary, cov_overall if with_cov else None)

                    # Store in session
                    st.session_state["tm_last_summary"] = summary
                    st.session_state["tm_last_report"] = report
                    st.session_state["tm_last_stdout"] = result.get("stdout", "")
                    st.session_state["tm_last_cov_modules"] = cov_modules
                    st.session_state["tm_last_cov_pct"] = cov_overall if with_cov else None

                    if summary["failed"] == 0 and summary["errors"] == 0:
                        st.success(f"✅ All {summary['passed']} tests passed in {summary['duration']}s!")
                    else:
                        st.error(f"❌ {summary['failed']} failures in {summary['total']} tests")
                    st.rerun()
                else:
                    st.warning("Tests ran but no JSON report generated.")
                    st.code(result.get("stdout", ""), language="text")
            else:
                st.error(f"❗ {result.get('error', 'Unknown error')}")

        # ── Results Panel ───────────────────────────────────
        report = st.session_state.get("tm_last_report")
        if report:
            st.markdown("---")
            st.subheader("📋 Results")

            rtab1, rtab2, rtab3, rtab4 = st.tabs([
                "📊 Breakdown", "❌ Failures", "🐌 Slow Tests", "📜 Raw Output"
            ])

            with rtab1:
                breakdown = _get_test_breakdown(report)
                if breakdown:
                    rows = []
                    for fp, c in sorted(breakdown.items()):
                        rows.append({
                            "Status": "✅" if c["failed"] == 0 else "❌",
                            "File": fp,
                            "Passed": c["passed"], "Failed": c["failed"],
                            "Total": c["total"],
                        })
                    st.dataframe(rows, use_container_width=True, hide_index=True)

            with rtab2:
                failures = _get_failed_tests(report)
                if failures:
                    for f in failures:
                        with st.expander(f"❌ `{f['nodeid']}` ({f['duration']}s)"):
                            st.code(f["message"], language="python")
                else:
                    st.success("No failures! 🎉")

            with rtab3:
                _render_slow_tests(report)

            with rtab4:
                stdout = st.session_state.get("tm_last_stdout", "")
                st.code(stdout if stdout else "No output captured.", language="text")

        # ── Coverage Heatmap ────────────────────────────────
        cov_modules = st.session_state.get("tm_last_cov_modules")
        st.markdown("---")
        _render_coverage_heatmap(cov_modules)

        # ── Test Explorer ───────────────────────────────────
        st.markdown("---")
        st.subheader("🗂️ Test Explorer")

        total_files = sum(len(v) for v in modules.values())
        st.caption(f"📁 {len(modules)} modules · 📄 {total_files} test files")

        for mod_name, files in sorted(modules.items()):
            icon = TEST_MODULES.get(mod_name, "📁")
            with st.expander(f"{icon} **{mod_name}/** — {len(files)} files"):
                for fi in files:
                    ca, cb = st.columns([5, 1])
                    ca.markdown(f"`{fi['name']}.py` — {fi['size_kb']} KB")
                    if cb.button("▶️", key=f"run_{fi['path']}"):
                        with st.spinner(f"Running {fi['name']}..."):
                            res = _run_pytest(fi["path"])
                        if res["success"]:
                            s = _parse_summary(res.get("report"))
                            if s and s["failed"] == 0:
                                st.success(f"✅ {s['passed']} passed ({s['duration']}s)")
                            elif s:
                                st.error(f"❌ {s['failed']} failed / {s['total']} total")

        # ── Flaky Tracker ───────────────────────────────────
        st.markdown("---")
        history = _load_history()
        _render_flaky_tracker(history)

        # ── History Chart ───────────────────────────────────
        st.markdown("---")
        st.subheader("📈 Run History")

        if history:
            import pandas as pd
            df = pd.DataFrame(history)
            df["run"] = range(1, len(df) + 1)

            # Main chart: pass/fail/skipped
            chart_cols = ["run", "passed", "failed", "skipped"]
            colors = ["#22c55e", "#ef4444", "#eab308"]

            # If coverage data exists, add it as a separate chart
            has_cov = any("coverage" in h for h in history)

            if has_cov:
                ch1, ch2 = st.columns([2, 1])
                with ch1:
                    st.area_chart(
                        df[chart_cols].set_index("run"),
                        color=colors,
                    )
                    st.caption("Test results trend")
                with ch2:
                    cov_data = df[["run", "coverage"]].dropna().set_index("run")
                    if not cov_data.empty:
                        st.line_chart(cov_data, color=["#3b82f6"])
                        st.caption("Coverage % trend")
            else:
                st.area_chart(
                    df[chart_cols].set_index("run"),
                    color=colors,
                )

            st.caption(f"Showing last {len(history)} runs")
        else:
            st.info("No history yet. Run tests to start tracking trends.")

    except Exception as e:
        st.error(f"❗ Test Manager Error: {e}")
        import traceback
        st.code(traceback.format_exc(), language="python")
