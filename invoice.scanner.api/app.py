from langchain_community.chat_models import ChatVertexAI
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage

import time

import os

from playwright.sync_api import sync_playwright

openai_api_key = os.getenv("OPENAI_API_KEY")
gcp_creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")








def call_llm(provider: str, prompt: str) -> str:
    """
    Call an LLM using LangChain.
    
    provider: "openai" or "gemini"
    prompt: text prompt to send
    """
    if provider.lower() == "openai":
        chat = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
    elif provider.lower() == "gemini":
        chat = ChatVertexAI(model_name="gemini-1.5", temperature=0.7)
        
    else:
        raise ValueError("Unsupported provider. Use 'openai' or 'gemini'.")

    response = chat.invoke([HumanMessage(content=prompt)])
    # response = chat([HumanMessage(content=prompt)])
    return response.content

# if __name__ == "__main__":


SEGMENT_NAME = "Båttrafik"

def scrape_allabolag_segment(segment_name):
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # headless=True för devcontainer/CI
        page = browser.new_page()
        page.goto("https://www.allabolag.se/segmentering")

        # Vänta på input-fältet
        page.wait_for_selector('input[placeholder="Sök segment"]')

        # Skriv segmentnamnet i input och tryck Enter
        page.fill('input[placeholder="Sök segment"]', segment_name)
        page.keyboard.press("Enter")
        time.sleep(2)  # vänta på att sidan laddas

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


    
