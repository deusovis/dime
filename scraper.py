import json
import cloudscraper
from bs4 import BeautifulSoup
import re

def scrape_blogabet():
    main_url = "https://dime.blogabet.com"
    picks_url = "https://dime.blogabet.com/blog/picks"
    
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})
    headers = {"X-Requested-With": "XMLHttpRequest"}
    cookies = {"ageVerified": "1"}
    
    final_data = {"stats": {"roi": "+0%", "units": "0.0"}, "picks": []}

    try:
        # 1. GET ROI AND UNITS
        main_res = scraper.get(main_url, cookies=cookies)
        main_soup = BeautifulSoup(main_res.text, 'html.parser')
        profit_elem = main_soup.find(id="header-profit")
        roi_elem = main_soup.find(id="header-yield")
        if profit_elem: final_data["stats"]["units"] = profit_elem.get_text(strip=True)
        if roi_elem: final_data["stats"]["roi"] = roi_elem.get_text(strip=True)

        # 2. GET 10 PICKS
        picks_res = scraper.get(picks_url, headers=headers, cookies=cookies)
        picks_soup = BeautifulSoup(picks_res.text, 'html.parser')
        pick_blocks = picks_soup.find_all('li', class_=re.compile(r'feed-pick'))
        
        seen_titles = set()
        for block in pick_blocks:
            if len(final_data["picks"]) >= 10: break 
            
            try:
                # MATCHUP & SELECTION
                matchup = block.find('h3').get_text(strip=True) if block.find('h3') else ""
                selection_elem = block.find(class_=re.compile(r'pick-line|pick-name|selection'))
                selection = selection_elem.get_text(strip=True) if selection_elem else matchup
                
                # CLEANING (ML Suffix Logic)
                clean_text = re.search(r'[^@]*', selection).group(0)
                clean_text = re.sub(r'\(.*?\)', '', clean_text)
                for term in [r'(?i)Spread', r'(?i)Game Lines', r'(?i)Odds', r'(?i)Handicap', r'(?i)Main']:
                    clean_text = re.sub(term, '', clean_text)
                
                if "MONEY LINE" in selection.upper() or "ML" in selection.upper():
                    team_name = re.sub(r'(?i)Money Line|ML', '', clean_text).strip()
                    if not team_name: team_name = matchup.split('-')[0].split('vs')[0].strip()
                    pick_title = f"{team_name} ML"
                else:
                    pick_title = clean_text.strip()

                if pick_title in seen_titles: continue
                seen_titles.add(pick_title)

                # --- THE STICKY FIX: FETCH DATE FROM POST ---
                date_text = "-"
                # Blogabet often puts the date in a div with class 'feed-date' or 'date'
                date_container = block.find(class_=re.compile(r'date|time|feed-date'))
                if date_container:
                    # This grabs the literal text (e.g. "21 Mar 2026")
                    date_text = " ".join(date_container.stripped_strings)
                    # Clean up if it grabbed time as well (e.g. "21 Mar 2026 14:00")
                    # We only want the first 3 parts: Day, Month, Year
                    parts = date_text.split()
                    if len(parts) >= 2:
                        date_text = " ".join(parts[:3])

                # ODDS
                all_text = block.get_text(" ")
                odds_val = "-"
                odds_match = re.search(r'@\s*(\d+\.?\d*)', all_text)
                if odds_match: odds_val = odds_match.group(1)
                
                # RESULT ENGINE (STRICT)
                result = "-"
                if block.find(class_=re.compile(r'label-success|text-green')):
                    result = "W"
                elif block.find(class_=re.compile(r'label-danger|text-red')):
                    result = "L"
                
                if result == "-":
                    upper_text = all_text.upper()
                    if "WON" in upper_text or "WIN" in upper_text: result = "W"
                    elif "LOST" in upper_text or "LOSE" in upper_text or "LOSS" in upper_text: result = "L"

                final_data["picks"].append({
                    "id": len(final_data["picks"]) + 1, 
                    "date": date_text.strip(), 
                    "pick": pick_title, 
                    "odds": odds_val, 
                    "result": result
                })
            except: continue
        
        with open('picks.json', 'w') as f:
            json.dump(final_data, f, indent=4)
        print("Success: Literal date and result text fetched.")

    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    scrape_blogabet()
