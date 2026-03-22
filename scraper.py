import json
import cloudscraper
from bs4 import BeautifulSoup
import datetime
import re

def scrape_blogabet():
    print("Connecting to Blogabet...")
    url = "https://dime.blogabet.com/blog/picks"
    
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})
    headers = {"X-Requested-With": "XMLHttpRequest"}
    cookies = {"ageVerified": "1"}
    
    try:
        response = scraper.get(url, headers=headers, cookies=cookies)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # FIX: We now look ONLY for <li> elements to prevent nested duplicates
        pick_blocks = soup.find_all('li', class_=re.compile(r'feed-pick'))
        
        new_picks = []
        seen_picks = set() # This tracks titles to prevent duplicates in one run
        
        for block in pick_blocks:
            if len(new_picks) >= 5: break # Keep only the last 5 unique items
            
            try:
                # 1. PICK TITLE (The Selection)
                title_elem = block.find('h3')
                pick_title = title_elem.get_text(strip=True) if title_elem else "Basketball Pick"
                
                # DE-DUPLICATION GUARD: Skip if we already processed this exact pick
                if pick_title in seen_picks:
                    continue
                seen_picks.add(pick_title)

                # 2. DATE
                date_elem = block.find(class_='feed-date')
                date_text = date_elem.get_text(strip=True) if date_elem else str(datetime.date.today())
                
                # 3. ODDS
                odds_val = "-"
                all_text = block.get_text(" ")
                odds_match = re.search(r'@\s*(\d+\.?\d*)', all_text)
                if odds_match:
                    odds_val = odds_match.group(1)
                
                # 4. RESULT (Enhanced Win/Loss detection)
                result = "-"
                # Check for Blogabet's specific color-coded labels
                if block.find(class_=re.compile(r'label-success|text-green|win|won')):
                    result = "W"
                elif block.find(class_=re.compile(r'label-danger|text-red|lose|lost')):
                    result = "L"
                
                # Backup: Check raw text if classes are hidden
                if result == "-":
                    upper_text = all_text.upper()
                    if any(word in upper_text for word in ["WON", "WIN", "PROFIT"]):
                        result = "W"
                    elif any(word in upper_text for word in ["LOST", "LOSE", "LOSS"]):
                        result = "L"

                new_picks.append({
                    "id": len(new_picks) + 1,
                    "date": date_text[:11],
                    "pick": pick_title,
                    "odds": odds_val,
                    "result": result
                })
                
            except Exception as e:
                print(f"Skipping pick due to error: {e}")
                continue
        
        if not new_picks:
            new_picks = [{"id": 1, "date": str(datetime.date.today()), "pick": "No picks found", "odds": "-", "result": "-"}]

        with open('picks.json', 'w') as f:
            json.dump(new_picks, f, indent=4)
        print(f"Successfully updated picks.json with {len(new_picks)} unique picks.")
        
    except Exception as e:
        print(f"Critical Scraper Error: {e}")

if __name__ == "__main__":
    scrape_blogabet()
