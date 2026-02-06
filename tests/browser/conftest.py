import pytest
from playwright.sync_api import Page, BrowserContext
import os
from datetime import datetime

# Default to diagnostics folder for artifacts
ARTIFACTS_DIR = "diagnostics"

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """
    Configure default browser context arguments.
    """
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "record_video_dir": os.path.join(ARTIFACTS_DIR, "videos"),
        "locale": "ar-SA" # Set locale to Arabic for Baloot
    }

@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    return {
        **browser_type_launch_args,
        "args": ["--font-render-hinting=none"] # Stabilize font rendering for consistent snapshots
    }

@pytest.fixture(autouse=True)
def setup_artifacts_dir():
    """Ensure artifacts directory exists."""
    if not os.path.exists(ARTIFACTS_DIR):
        os.makedirs(ARTIFACTS_DIR)

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Capture screenshot on test failure.
    """
    outcome = yield
    rep = outcome.get_result()
    
    if rep.when == "call" and rep.failed:
        page = item.funcargs.get("page")
        if page:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(ARTIFACTS_DIR, f"failure_{item.name}_{timestamp}.png")
            try:
                page.screenshot(path=screenshot_path)
                print(f"\n📸 Failure screenshot saved: {screenshot_path}")
                
                # Save HTML source
                html_path = os.path.join(ARTIFACTS_DIR, f"failure_{item.name}_{timestamp}.html")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(page.content())
                print(f"📄 Page HTML saved: {html_path}")

                # Also print page text context
                print(f"\n📄 Page URL: {page.url}")
            except Exception as e:
                print(f"\n⚠️ Failed to take screenshot: {e}")
