import json
import requests
from bs4 import BeautifulSoup
import datetime

def scrape_blogabet():
    print("Connecting to Blogabet hidden data endpoint...")
    
    # 1. Target the exact backend URL where the picks are actually generated
    url = "https://dime.blogabet.com/blog/picks"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest" # Tells the server we are making a valid AJAX request
    }
    
    # 2. Inject the age verification cookie so Blogabet doesn't block us with the 18+ popup
    cookies = {
        "ageVerified": "1"
    }
    
    try:
        response = requests.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all individual pick blocks
        pick_blocks = soup.find_all('li', class_='feed-pick')
        
        new_picks = []
        
        # Grab only the first 5 picks
        for index, block in enumerate(pick_blocks[:5]):
            try:
                # Extract the Date
                date_elem = block.find('div', class_='feed-date')
                date_text = date_elem.text.strip() if date_elem else str(datetime.date.today())
                
                # Extract the Pick Name (Team/Selection)
                title_elem = block.find('h3')
                pick_title = title_elem.text.strip() if title_elem else "Basketball Pick"
                
                # Extract the Odds
                odds_elem = block.find('div', class_='pick-odds')
                # Blogabet sometimes puts the odds inside a bold tag inside the pick-odds div
                odds_val = odds_elem.find('strong').text.strip() if odds_elem and odds_elem.find('strong') else (odds_elem.text.strip() if odds_elem else "-")
                
                # Determine Result (W, L, or Pending) based on the CSS class
                result = "-"
                block_classes = block.get('class', [])
                
                # Check for win/loss classes (Blogabet uses 'win', 'lose', 'half-win', 'half-lose', 'void', 'draw')
                if 'win' in block_classes or 'half-win' in block_classes:
                    result = "W"
                elif 'lose' in block_classes or 'half-lose' in block_classes:
                    result = "L"
                elif 'void' in block_classes or 'draw' in block_classes:
                    result = "V"
                    
                new_picks.append({
                    "id": index + 1,
                    "date": date_text[:10], # Format to YYYY-MM-DD
                    "pick": pick_title,
                    "odds": odds_val,
                    "result": result
                })
                
            except Exception as e:
                print(f"Skipping a pick due to parsing error: {e}")
                continue
        
        if not new_picks:
            print("Could not find any picks on the backend URL. Check if Blogabet changed their layout.")
            new_picks = [
                {"id": 1, "date": str(datetime.date.today()), "pick": "Awaiting Live Scraper...", "odds": "-", "result": "-"}
            ]

        with open('picks.json', 'w') as f:
            json.dump(new_picks, f, indent=4)
            
        print(f"Successfully saved {len(new_picks)} picks to picks.json")
        
    except Exception as e:
        print(f"Critical Scraper Error: {e}")

if __name__ == "__main__":
    scrape_blogabet()
