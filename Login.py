import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        page = await context.new_page()
        await page.goto("https://www.instagram.com/")

        print("⏳ Please log in to Instagram manually...")
        print("✅ After login, close the browser window to continue.")

        # Wait for user to login and manually close the browser
        await page.wait_for_timeout(120000)  # wait 2 mins max
        await context.storage_state(path="state.json")

        print("🎉 Login saved to state.json")

        await browser.close()

asyncio.run(run())
