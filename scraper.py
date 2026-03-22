import json
import cloudscraper
from bs4 import BeautifulSoup
import datetime

def scrape_blogabet():
    print("Connecting to Blogabet using Cloudscraper...")
    url = "https://dime.blogabet.com/blog/picks"
    
    scraper = cloudscraper.create_scraper(browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    })
    
    headers = {"X-Requested-With": "XMLHttpRequest"}
    cookies = {"ageVerified": "1"}
    
    try:
        response = scraper.get(url, headers=headers, cookies=cookies)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        pick_blocks = soup.find_all(['li', 'div'], class_='feed-pick')
        new_picks = []
        
        for index, block in enumerate(pick_blocks[:5]):
            try:
                # 1. Date
                date_elem = block.find(class_='feed-date')
                date_text = date_elem.text.strip() if date_elem else str(datetime.date.today())
                
                # 2. Pick Title
                title_elem = block.find('h3')
                pick_title = title_elem.text.strip() if title_elem else "Basketball Pick"
                
                # 3. Odds - Aggressive Search
                odds_val = "-"
                odds_elem = block.find(class_='pick-odds')
                if odds_elem and odds_elem.text.strip():
                    odds_val = odds_elem.text.replace('@', '').strip()
                else:
                    # Look everywhere in the block for the '@' symbol
                    for el in block.find_all(['span', 'div', 'strong', 'button', 'a']):
                        if el.text and '@' in el.text and len(el.text) < 15:
                            odds_val = el.text.replace('@', '').strip()
                            break
                            
                # Clean up odds formatting
                odds_val = odds_val.split('\n')[0].strip()

                # 4. Result - Aggressive Search
                result = "-"
                # Check for Bootstrap label classes
                labels = block.find_all(class_='label')
                for label in labels:
                    lbl_text = label.text.strip().upper()
                    if lbl_text in ['WIN', 'WON', 'HALF-WIN', 'HALF WIN']:
                        result = "W"
                    elif lbl_text in ['LOSE', 'LOST', 'HALF-LOSE', 'HALF LOSE']:
                        result = "L"
                    elif lbl_text in ['VOID', 'DRAW', 'REFUND', 'PUSH']:
                        result = "V"
                
                # If still nothing, check raw HTML for color classes
                if result == "-":
                    block_html = str(block).lower()
                    if 'label-success' in block_html or 'bg-success' in block_html or 'won' in block_html:
                        result = "W"
                    elif 'label-danger' in block_html or 'bg-danger' in block_html or 'lost' in block_html:
                        result = "L"
                    elif 'label-default' in block_html or 'bg-warning' in block_html:
                        result = "V"
                    
                new_picks.append({
                    "id": index + 1,
                    "date": date_text[:10],
                    "pick": pick_title,
                    "odds": odds_val,
                    "result": result
                })
                
                # Debugging log: Prints the raw HTML of the first pick to help us if it fails again
                if index == 0:
                    print("--- DEBUG: HTML of First Pick ---")
                    print(str(block)[:1000])
                    print("---------------------------------")
                
            except Exception as e:
                print(f"Parsing error on individual pick: {e}")
                continue
        
        if not new_picks:
            print("Failed to parse picks. Reverting to fallback data.")
            new_picks = [
                {"id": 1, "date": str(datetime.date.today()), "pick": "Awaiting Live Scraper...", "odds": "-", "result": "-"}
            ]

        with open('picks.json', 'w') as f:
            json.dump(new_picks, f, indent=4)
            
        print(f"Successfully scraped and saved {len(new_picks)} picks.")
        
    except Exception as e:
        print(f"Critical Scraper Error: {e}")

if __name__ == "__main__":
    scrape_blogabet()
