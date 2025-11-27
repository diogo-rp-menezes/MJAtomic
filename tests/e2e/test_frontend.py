import threading
import time
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from playwright.sync_api import Page, expect

# --- Test Setup ---
# We need a simple server to host the static dashboard for Playwright to access.

PORT = 8002
BASE_URL = f"http://localhost:{PORT}"

app = FastAPI()
app.mount("/", StaticFiles(directory="src/services/api_gateway/static", html=True), name="static")

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=PORT)

# --- E2E Tests ---

def test_dashboard_loads(page: Page):
    """
    Tests if the dashboard page loads correctly.
    """
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(2)  # Give the server a moment to start

    page.goto(BASE_URL)
    
    # Check if the main title is visible
    expect(page.locator("h1")).to_have_text("DevAgent Dashboard")

def test_create_plan_ui(page: Page):
    """
    Tests the UI interaction for creating a new plan.
    """
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(2)

    page.goto(BASE_URL)

    # Fill the input and click the button
    page.fill("input[type='text']", "New Test Project")
    page.click("button")

    # Check if the new plan appears in the list
    expect(page.locator("h3")).to_have_text("New Test Project")
