from playwright.sync_api import sync_playwright

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSevc8dcRaDPUy4sbiinMPzb46abJhUkjknm91pfQ9WFj_5qtQ/viewform"


def request_problem_set(leader_name: str, email: str) -> bool:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(FORM_URL, wait_until="domcontentloaded")

        # Fill text inputs
        page.get_by_label("Team Lead Name").fill(leader_name)
        page.get_by_label("Email").fill(email)

        # Select radio option correctly
        page.get_by_role("radio", name="Yes").click()

        # Submit
        page.get_by_role("button", name="Submit").click()

        page.wait_for_timeout(2000)
        browser.close()

    return True
