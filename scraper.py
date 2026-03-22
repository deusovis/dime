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
        pick_blocks = soup.find_all('li', class_=re.compile(r'feed-pick'))
        
        new_picks = []
        seen_titles = set()
        
        for block in pick_blocks:
            if len(new_picks) >= 5: break
            
            try:
                # 1. MATCHUP vs ACTUAL PICK
                # Matchup is often "Team A - Team B"
                matchup = block.find('h3').get_text(strip=True) if block.find('h3') else ""
                
                # Selection is the specific handicap/pick (e.g., "Fribourg -34.5")
                selection_elem = block.find(class_=re.compile(r'pick-line|pick-name|selection'))
                selection = selection_elem.get_text(strip=True) if selection_elem else ""
                
                # Use the specific selection (handicap) if found, otherwise matchup
                pick_title = selection if selection else matchup
                
                # MONEY LINE EXCEPTION
                if "MONEY LINE" in pick_title.upper() or "MONEY LINE" in matchup.upper():
                    # If the matchup contains the team and it's a Money Line bet
                    # Clean up the name to "Team Money Line"
                    base_name = selection.replace("Money Line", "").replace("ML", "").strip()
                    if not base_name: # Fallback to the first team in the matchup
                        base_name = matchup.split('-')[0].split('vs')[0].strip()
                    pick_title = f"{base_name} Money Line"

                if pick_title in seen_titles: continue
                seen_titles.add(pick_title)

                # 2. DATE (Smarter Span Joining)
                date_container = block.find(class_=re.compile(r'feed-date|date'))
                if date_container:
                    spans = date_container.find_all('span')
                    date_text = " ".join([s.get_text(strip=True) for s in spans]) if spans else date_container.get_text(strip=True)
                else:
                    date_text = str(datetime.date.today())

                # 3. ODDS
                all_text = block.get_text(" ")
                odds_val = "-"
                odds_match = re.search(r'@\s*(\d+\.?\d*)', all_text)
                if odds_match: odds_val = odds_match.group(1)
                
                # 4. RESULT
                result = "-"
                if block.find(class_=re.compile(r'label-success|text-green|win|won')):
                    result = "W"
                elif block.find(class_=re.compile(r'label-danger|text-red|lose|lost')):
                    result = "L"
                elif "WON" in all_text.upper() or "WIN" in all_text.upper():
                    result = "W"
                elif "LOST" in all_text.upper() or "LOSE" in all_text.upper():
                    result = "L"

                new_picks.append({
                    "id": len(new_picks) + 1,
                    "date": date_text.strip(),
                    "pick": pick_title,
                    "odds": odds_val,
                    "result": result
                })
                
            except Exception as e:
                print(f"Skipping pick due to error: {e}")
                continue
        
        with open('picks.json', 'w') as f:
            json.dump(new_picks, f, indent=4)
        print(f"Successfully updated picks.json with {len(new_picks)} picks.")
        
    except Exception as e:
        print(f"Critical Scraper Error: {e}")

if __name__ == "__main__":
    scrape_blogabet()
