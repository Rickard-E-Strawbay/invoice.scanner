import os
from flask import Flask

openai_api_key = os.getenv("OPENAI_API_KEY")
gcp_creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        # Klicka på segmentet (första träffen)
        page.click(f'text="{segment_name}"')
        page.wait_for_load_state("networkidle")

        # Loop över paginering
        while True:
            # Vänta på tabellen med företag
            page.wait_for_selector("table tbody tr")

            rows = page.query_selector_all("table tbody tr")
            for row in rows:
                name = row.query_selector("td a").inner_text().strip()
                link = row.query_selector("td a").get_attribute("href")
                orgnr = row.query_selector("td:nth-child(2)").inner_text().strip()
                turnover = row.query_selector("td:nth-child(3)").inner_text().strip()
                num_employees = row.query_selector("td:nth-child(4)").inner_text().strip()
                address = row.query_selector("td:nth-child(5)").inner_text().strip()

                results.append({
                    "name": name,
                    "orgnr": orgnr,
                    "allabolag_link": f"https://www.allabolag.se{link}",
                    "turnover": turnover,
                    "num_employees": num_employees,
                    "address": address
                })

            # Kolla om "Nästa" knapp finns och är klickbar
            next_button = page.query_selector("a[rel='next']")
            if next_button and "disabled" not in next_button.get_attribute("class"):
                next_button.click()
                page.wait_for_load_state("networkidle")
            else:
                break

        browser.close()
    return results

if __name__ == "__main__":
    data = scrape_allabolag_segment(SEGMENT_NAME)
    print(f"Hittade {len(data)} företag:")
    for item in data[:5]:  # visa de första 5 som exempel
        print(item)
    

    # print("Python executable:", sys.executable)
    # print("Python version:", sys.version)
    # print("LangChain installed:", "langchain" in sys.modules or "langchain" in dir())

  

    # Call GPT
    prompt = "Search for information about t-bone steaks and how to best cook it using a sous vide to perfection. Output it as a nicely formatted ASCII command prompt."
    # gpt_response = call_llm("openai", prompt)
    # print("GPT Response:\n", gpt_response)

    # Call Gemini
    # gemini_response = call_llm("gemini", prompt)
    # print("\nGemini Response:\n", gemini_response)

    # with sync_playwright() as p:
        # Välj webbläsare (chromium, firefox, webkit)
        # browser = p.chromium.launch(headless=False)  # headless=False visar webbläsaren
        # page = browser.new_page()

        # Gå till en webbsida
        # page.goto("https://google.com")

        # Ta en skärmdump
        # page.screenshot(path="example.png")
        # print("Skärmdump tagen!")

        # Skriv ut sidans titel
        # print("Sidans titel:", page.title())

        # Stäng webbläsaren
        # browser.close()


    
