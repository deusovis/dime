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
        
        # --- NEW: SCRAPE HEADER STATS ---
        profit_elem = soup.find(id="header-profit")
        roi_elem = soup.find(id="header-yield")
        
        stats = {
            "units": profit_elem.get_text(strip=True) if profit_elem else "+0.0",
            "roi": roi_elem.get_text(strip=True) if roi_elem else "+0%"
        }

        # --- SCRAPE PICKS ---
        pick_blocks = soup.find_all('li', class_=re.compile(r'feed-pick'))
        picks_list = []
        seen_titles = set()
        
        for block in pick_blocks:
            if len(picks_list) >= 30: break 
            try:
                matchup = block.find('h3').get_text(strip=True) if block.find('h3') else ""
                selection_elem = block.find(class_=re.compile(r'pick-line|pick-name|selection'))
                selection = selection_elem.get_text(strip=True) if selection_elem else matchup
                
                # Cleaning
                clean_text = re.search(r'[^@]*', selection).group(0)
                clean_text = re.sub(r'\(.*?\)', '', clean_text)
                unwanted = [r'(?i)Spread', r'(?i)Game Lines', r'(?i)Odds', r'(?i)Handicap', r'(?i)Main']
                for term in unwanted: clean_text = re.sub(term, '', clean_text)
                
                # ML Rule
                if "MONEY LINE" in selection.upper() or "ML" in selection.upper():
                    team_name = re.sub(r'(?i)Money Line|ML', '', clean_text).strip()
                    if not team_name: team_name = matchup.split('-')[0].split('vs')[0].strip()
                    pick_title = f"{team_name} ML"
                else:
                    pick_title = clean_text.strip()

                if pick_title in seen_titles: continue
                seen_titles.add(pick_title)

                # Date, Odds, Result
                date_container = block.find(class_=re.compile(r'feed-date|date'))
                date_text = " ".join([s.get_text(strip=True) for s in date_container.find_all('span')]) if date_container and date_container.find_all('span') else (date_container.get_text(strip=True) if date_container else str(datetime.date.today()))

                all_text = block.get_text(" ")
                odds_val = "-"
                odds_match = re.search(r'@\s*(\d+\.?\d*)', all_text)
                if odds_match: odds_val = odds_match.group(1)
                
                result = "-"
                if block.find(class_=re.compile(r'label-success|text-green|win|won')):
                    result = "W"
                elif block.find(class_=re.compile(r'label-danger|text-red|lose|lost')):
                    result = "L"
                elif "WON" in all_text.upper() or "WIN" in all_text.upper():
                    result = "W"
                elif "LOST" in all_text.upper() or "LOSE" in all_text.upper():
                    result = "L"

                picks_list.append({
                    "id": len(picks_list) + 1,
                    "date": date_text.strip(),
                    "pick": pick_title,
                    "odds": odds_val,
                    "result": result
                })
            except: continue
        
        # SAVE STRUCTURED DATA
        final_data = {
            "stats": stats,
            "picks": picks_list
        }
        
        with open('picks.json', 'w') as f:
            json.dump(final_data, f, indent=4)
        print(f"Updated with ROI: {stats['roi']} and Units: {stats['units']}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    scrape_blogabet()
