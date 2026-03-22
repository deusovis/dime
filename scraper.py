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
        pick_blocks = soup.find_all(['li', 'div'], class_='feed-pick')
        new_picks = []
        
        for index, block in enumerate(pick_blocks[:5]):
            try:
                # 1. DATE
                date_elem = block.find(class_='feed-date')
                date_text = date_elem.text.strip() if date_elem else str(datetime.date.today())
                
                # 2. PICK TITLE
                title_elem = block.find('h3')
                pick_title = title_elem.text.strip() if title_elem else "Basketball Pick"
                
                # 3. ODDS (The Detective Search)
                odds_val = "-"
                # Search for any text containing '@'
                odds_search = block.find(text=re.compile(r'@'))
                if odds_search:
                    # Extract the number following the @
                    match = re.search(r'@\s*(\d+\.?\d*)', odds_search)
                    if match:
                        odds_val = match.group(1)
                
                # 4. RESULT (The Badge Search)
                result = "-"
                block_classes = block.get('class', [])
                full_text = block.get_text().upper()
                
                # Check CSS Classes first (most reliable)
                if any(x in block_classes for x in ['win', 'half-win']):
                    result = "W"
                elif any(x in block_classes for x in ['lose', 'lost', 'half-lose']):
                    result = "L"
                # Check visible labels/text if classes are missing
                elif "WON" in full_text or "WIN" in full_text:
                    result = "W"
                elif "LOST" in full_text or "LOSE" in full_text:
                    result = "L"
                elif "VOID" in full_text or "PUSH" in full_text or "CANCELLED" in full_text:
                    result = "V"
                    
                new_picks.append({
                    "id": index + 1,
                    "date": date_text[:10],
                    "pick": pick_title,
                    "odds": odds_val,
                    "result": result
                })
                
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
