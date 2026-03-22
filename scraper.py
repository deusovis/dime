import json
import cloudscraper
from bs4 import BeautifulSoup
import datetime
import re

def scrape_blogabet():
    print("Connecting to Blogabet AJAX endpoint...")
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
        # Blogabet returns raw HTML for the picks tab
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Blogabet picks are usually <li> items with the 'feed-pick' class
        pick_blocks = soup.find_all('li', class_=re.compile(r'feed-pick'))
        
        new_picks = []
        
        for index, block in enumerate(pick_blocks[:5]):
            try:
                # 1. DATE
                date_elem = block.find(class_='feed-date')
                date_text = date_elem.get_text(strip=True) if date_elem else str(datetime.date.today())
                
                # 2. PICK TITLE (The Selection)
                title_elem = block.find('h3')
                pick_title = title_elem.get_text(strip=True) if title_elem else "Basketball Pick"
                
                # 3. ODDS (Looking specifically for the '@' pattern)
                odds_val = "-"
                # Check the standard odds container first
                odds_container = block.find(class_='pick-odds')
                if odds_container:
                    odds_val = odds_container.get_text(strip=True).replace('@', '').strip()
                
                # If still blank, search all text in the block for an '@' symbol
                if odds_val == "-" or not odds_val:
                    all_text = block.get_text(" ")
                    match = re.search(r'@\s*(\d+\.?\d*)', all_text)
                    if match:
                        odds_val = match.group(1)
                
                # 4. RESULT (Win/Loss Detection)
                result = "-"
                # A) Check classes on the main <li> tag (most reliable)
                classes = block.get('class', [])
                if any(c in classes for c in ['win', 'half-win', 'won']):
                    result = "W"
                elif any(c in classes for c in ['lose', 'lost', 'half-lose']):
                    result = "L"
                
                # B) If classes didn't work, check for green/red labels inside
                if result == "-":
                    labels = block.find_all(class_=re.compile(r'label|badge'))
                    for label in labels:
                        label_text = label.get_text(strip=True).upper()
                        if 'WON' in label_text or 'WIN' in label_text:
                            result = "W"
                            break
                        elif 'LOST' in label_text or 'LOSE' in label_text:
                            result = "L"
                            break

                new_picks.append({
                    "id": index + 1,
                    "date": date_text[:11], # Takes "21 Mar 2026"
                    "pick": pick_title,
                    "odds": odds_val,
                    "result": result
                })
                
            except Exception as e:
                print(f"Error parsing pick {index}: {e}")
                continue
        
        if not new_picks:
            print("No picks found in the AJAX response.")
            new_picks = [{"id": 1, "date": str(datetime.date.today()), "pick": "No picks found", "odds": "-", "result": "-"}]

        with open('picks.json', 'w') as f:
            json.dump(new_picks, f, indent=4)
            
        print(f"Successfully updated picks.json with {len(new_picks)} picks.")
        
    except Exception as e:
        print(f"Critical Scraper Error: {e}")

if __name__ == "__main__":
    scrape_blogabet()
