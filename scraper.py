import json
import cloudscraper
from bs4 import BeautifulSoup
import datetime
import re

def scrape_blogabet():
    print("Connecting to Blogabet AJAX endpoint...")
    url = "https://dime.blogabet.com/blog/picks"
    
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})
    headers = {"X-Requested-With": "XMLHttpRequest"}
    cookies = {"ageVerified": "1"}
    
    try:
        response = scraper.get(url, headers=headers, cookies=cookies)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        pick_blocks = soup.find_all(['li', 'div'], class_=re.compile(r'feed-pick'))
        new_picks = []
        
        for index, block in enumerate(pick_blocks[:5]):
            try:
                # 1. DATE
                date_elem = block.find(class_='feed-date')
                date_text = date_elem.get_text(strip=True) if date_elem else str(datetime.date.today())
                
                # 2. PICK TITLE
                title_elem = block.find('h3')
                pick_title = title_elem.get_text(strip=True) if title_elem else "Basketball Pick"
                
                # 3. ODDS (Regular Expression Search)
                odds_val = "-"
                all_text = block.get_text(" ")
                odds_match = re.search(r'@\s*(\d+\.?\d*)', all_text)
                if odds_match:
                    odds_val = odds_match.group(1)
                
                # 4. RESULT (The "Profit Detector" Logic)
                result = "-"
                # Check for + (Win) or - (Loss) followed by a number that isn't the handicap
                # We look for strings like "+0.80" or "-1.00" or "+12.50"
                profit_match = re.search(r'([+-])\d+\.\d{2}', all_text)
                
                if profit_match:
                    symbol = profit_match.group(1)
                    result = "W" if symbol == "+" else "L"
                
                # Backup: Check for words or specific classes if profit is missing
                if result == "-":
                    upper_text = all_text.upper()
                    if "WON" in upper_text or "WIN" in upper_text:
                        result = "W"
                    elif "LOST" in upper_text or "LOSE" in upper_text:
                        result = "L"
                
                new_picks.append({
                    "id": index + 1,
                    "date": date_text[:11],
                    "pick": pick_title,
                    "odds": odds_val,
                    "result": result
                })
                
                # --- LOGGING FOR YOU TO CHECK ---
                if index == 0:
                    print(f"--- DEBUG PICK 1 ---")
                    print(f"Text found: {all_text[:200]}...")
                    print(f"Detected Odds: {odds_val} | Detected Result: {result}")
                
            except Exception as e:
                print(f"Error parsing pick {index}: {e}")
                continue
        
        if not new_picks:
            new_picks = [{"id": 1, "date": str(datetime.date.today()), "pick": "No picks found", "odds": "-", "result": "-"}]

        with open('picks.json', 'w') as f:
            json.dump(new_picks, f, indent=4)
        print(f"Successfully updated picks.json with {len(new_picks)} picks.")
        
    except Exception as e:
        print(f"Critical Scraper Error: {e}")

if __name__ == "__main__":
    scrape_blogabet()
