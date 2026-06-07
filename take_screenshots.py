"""Take screenshots of the LearnPath AI app for README."""
import asyncio
from playwright.async_api import async_playwright
import os

BASE = "http://localhost:8000"
OUT  = "docs/screenshots"
os.makedirs(OUT, exist_ok=True)

async def screenshot(page, path, scroll=0):
    if scroll:
        await page.evaluate(f"window.scrollTo(0, {scroll})")
        await page.wait_for_timeout(400)
    await page.screenshot(path=path, full_page=False)
    print(f"  saved: {path}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 820})

        # ── 1. Hero / Home ─────────────────────────────────────────────
        print("1. Hero page...")
        await page.goto(BASE, wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await screenshot(page, f"{OUT}/1_hero.png")

        # ── 2. Recommendations ────────────────────────────────────────
        print("2. Recommendations...")
        await page.evaluate("""() => {
            addSkill('python');
            addSkill('machine learning');
            addSkill('statistics');
            document.getElementById('target-role').value = 'Data Scientist';
        }""")
        await page.click("button#rec-btn")
        await page.wait_for_timeout(3000)
        await page.evaluate("window.scrollTo(0, 320)")
        await page.wait_for_timeout(400)
        await screenshot(page, f"{OUT}/2_recommendations.png")

        # ── 3. AI Explain ─────────────────────────────────────────────
        print("3. AI Explain...")
        await page.evaluate("""() => {
            const keys = [...courseStore.keys()];
            if (keys.length) aiExplain(keys[0]);
        }""")
        await page.wait_for_timeout(4000)
        await screenshot(page, f"{OUT}/3_ai_explain.png")

        # ── 4. Skill Gap ──────────────────────────────────────────────
        print("4. Skill Gap...")
        await page.evaluate("switchTab('gap')")
        await page.wait_for_timeout(400)
        await page.fill("#gap-skills", "python, sql, excel")
        await page.fill("#gap-role", "Machine Learning Engineer")
        await page.click("button#gap-btn")
        await page.wait_for_timeout(2500)
        await screenshot(page, f"{OUT}/4_skill_gap.png")

        # ── 5. Roadmap ────────────────────────────────────────────────
        print("5. Roadmap...")
        await page.evaluate("switchTab('roadmap')")
        await page.wait_for_timeout(400)
        await page.fill("#rm-skills", "python, sql")
        await page.fill("#rm-role", "Data Scientist")
        await page.click("button#rm-btn")
        await page.wait_for_timeout(2500)
        await screenshot(page, f"{OUT}/5_roadmap.png")

        # ── 6. Resume ─────────────────────────────────────────────────
        print("6. Resume Analyzer...")
        await page.evaluate("switchTab('resume')")
        await page.wait_for_timeout(400)
        await page.fill("#resume-text", "Experienced Python developer with 3 years in ML. Proficient in scikit-learn, pandas, numpy, TensorFlow. Built NLP pipelines and recommender systems. Strong SQL and AWS SageMaker experience.")
        await page.fill("#resume-role", "Data Scientist")
        await page.click("button#resume-btn")
        await page.wait_for_timeout(4000)
        await screenshot(page, f"{OUT}/6_resume.png")

        # ── 7. AI Advisor ─────────────────────────────────────────────
        print("7. AI Advisor...")
        await page.evaluate("switchTab('advisor')")
        await page.wait_for_timeout(400)
        await page.fill("#adv-skills", "python, machine learning, sql")
        await page.fill("#adv-role", "Data Scientist")
        await page.fill("#adv-exp", "1")
        await page.select_option("#adv-edu", "Bachelor's Degree")
        await page.click("button#adv-btn")
        await page.wait_for_timeout(5000)
        await screenshot(page, f"{OUT}/7_ai_advisor.png")

        await browser.close()
        print("\n✅ All screenshots saved to docs/screenshots/")

asyncio.run(main())
