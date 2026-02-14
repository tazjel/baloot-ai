from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://localhost:5173/react-py4web/static/build/")

    print("Navigated to page")

    # Wait for the Auth button (top left)
    # It has text "دخول" or Icon.
    try:
        page.wait_for_selector("text=دخول", timeout=5000)
        print("Found Login button")
    except:
        print("Login button not found in 5s")
        page.screenshot(path="verification/error_lobby.png")
        browser.close()
        return

    # Take screenshot of Lobby
    page.screenshot(path="verification/step1_lobby.png")

    # Click Login
    page.get_by_text("دخول").click()
    print("Clicked Login")

    # Wait for Modal "تسجيل الدخول"
    try:
        page.wait_for_selector("text=تسجيل الدخول", timeout=5000)
        print("Found Modal")
    except:
        print("Modal not found in 5s")
        page.screenshot(path="verification/error_modal.png")
        browser.close()
        return

    # Take screenshot of Modal
    page.screenshot(path="verification/step2_modal.png")

    browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
