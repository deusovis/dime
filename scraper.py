import json
import requests
from bs4 import BeautifulSoup
import datetime

def scrape_blogabet():
    print("Connecting to Blogabet...")
    url = "https://dime.blogabet.com/"
    
    # We use a User-Agent so Blogabet thinks this is a normal web browser, not a robot
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for the blocks of HTML that contain the picks (Blogabet usually uses 'feed-pick' or 'pick-line')
        # Note: If Blogabet updates their site design, these class names might need a quick tweak!
        pick_blocks = soup.find_all('li', class_='feed-pick', limit=5)
        
        new_picks = []
        
        for index, block in enumerate(pick_blocks):
            try:
                # Extract the Date, Pick Name, and Odds
                date_text = block.find('div', class_='feed-date').text.strip() if block.find('div', class_='feed-date') else str(datetime.date.today())
                pick_title = block.find('h3').text.strip() if block.find('h3') else "Basketball Pick"
                odds_val = block.find('div', class_='pick-odds').text.strip() if block.find('div', class_='pick-odds') else "-"
                
                # Determine Result based on the CSS class applied to the pick (win/loss/half-win/etc)
                result = "-"
                block_classes = block.get('class', [])
                if 'win' in block_classes or 'half-win' in block_classes:
                    result = "W"
                elif 'lose' in block_classes or 'half-lose' in block_classes:
                    result = "L"
                elif 'draw' in block_classes or 'void' in block_classes:
                    result = "V"
                    
                new_picks.append({
                    "id": index + 1,
                    "date": date_text[:10], # Keeps just the YYYY-MM-DD part
                    "pick": pick_title,
                    "odds": odds_val,
                    "result": result
                })
                
            except Exception as e:
                print(f"Skipping a pick due to parsing error: {e}")
                continue
        
        # If the scraper couldn't find any picks (e.g., if Blogabet blocked the request or changed their HTML)
        if not new_picks:
            print("Could not find any picks. Pushing fallback data to keep the site layout intact.")
            new_picks = [
                {"id": 1, "date": str(datetime.date.today()), "pick": "Awaiting Latest Pick...", "odds": "-", "result": "-"}
            ]

        # Save the freshly scraped data into our JSON file
        with open('picks.json', 'w') as f:
            json.dump(new_picks, f, indent=4)
            
        print(f"Successfully saved {len(new_picks)} picks to picks.json")
        
    except Exception as e:
        print(f"Critical Scraper Error: {e}")

if __name__ == "__main__":
    scrape_blogabet()
