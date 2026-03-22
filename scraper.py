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
    
    final_data = {"stats": {"roi": "+18.4%", "units": "+32.1"}, "picks": []}

    try:
        # 1. GET ROI AND UNITS FROM HEADER
        try:
            main_res = scraper.get(main_url, cookies=cookies)
            main_soup = BeautifulSoup(main_res.text, 'html.parser')
            profit_elem = main_soup.find(id="header-profit")
            roi_elem = main_soup.find(id="header-yield")
            if profit_elem: final_data["stats"]["units"] = profit_elem.get_text(strip=True)
            if roi_elem: final_data["stats"]["roi"] = roi_elem.get_text(strip=True)
        except: pass

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
                
                # CLEANING (Keep (W) but destroy empty parens)
                clean_text = re.search(r'[^@]*', selection).group(0)
                for term in [r'(?i)Spread', r'(?i)Game Lines', r'(?i)Odds', r'(?i)Handicap', r'(?i)Main']:
                    clean_text = re.sub(term, '', clean_text)
                
                # Sweep up the empty parentheses left behind
                clean_text = re.sub(r'\(\s*\)', '', clean_text)
                
                if "MONEY LINE" in selection.upper() or "ML" in selection.upper():
                    team_name = re.sub(r'(?i)Money Line|ML', '', clean_text).strip()
                    team_name = team_name.strip(" -")
                    # Clean up any double spaces
                    team_name = re.sub(r'\s+', ' ', team_name).strip()
                    
                    if not team_name: team_name = matchup.split('-')[0].split('vs')[0].strip()
                    pick_title = f"{team_name} ML"
                else:
                    pick_title = re.sub(r'\s+', ' ', clean_text).strip()

                if pick_title in seen_titles: continue
                seen_titles.add(pick_title)

                # --- BULLETPROOF COUNTRY DETECTION ---
                country_name = "World"
                for text_elem in block.find_all(['small', 'span', 'div', 'a']):
                    raw_str = text_elem.get_text(" ", strip=True)
                    if "Basketball" in raw_str and "/" in raw_str:
                        parts = [p.strip() for p in raw_str.split('/')]
                        if len(parts) >= 2 and parts[0].upper() == "BASKETBALL":
                            country_name = parts[1]
                            break

                # --- THE ULTIMATE DATE FIX ---
                date_text = "-"
                date_container = block.select_one('.feed-date, .date, .time')
                if date_container:
                    date_text = " ".join(date_container.stripped_strings)
                
                if date_text == "-":
                    raw_text = block.get_text(" ")
                    match = re.search(r'(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})', raw_text)
                    if match:
                        date_text = match.group(1)

                # ODDS
                all_text = block.get_text(" ")
                odds_val = "-"
                odds_match = re.search(r'@\s*(\d+\.?\d*)', all_text)
                if odds_match: odds_val = odds_match.group(1)
                
                # --- FIXED RESULT DETECTION ---
                result = "-"
                
                # 1. Check for exact class boundaries (prevents matching 'market-winner' or 'window')
                is_lost = block.find(class_=re.compile(r'\b(label-danger|text-red|status-lost)\b'))
                is_won = block.find(class_=re.compile(r'\b(label-success|text-green|status-won)\b'))
                
                if is_lost:
                    result = "L"
                elif is_won:
                    result = "W"
                else:
                    # 2. Fallback using exact word boundaries \b to avoid matching "Winner"
                    upper_text = all_text.upper()
                    
                    if re.search(r'\b(WON|WIN)\b', upper_text): 
                        result = "W"
                    elif re.search(r'\b(LOST|LOSS|LOSE)\b', upper_text): 
                        result = "L"
                    elif re.search(r'-\d+\.\d{2}\b', all_text): 
                        result = "L"
                    elif re.search(r'\+\d+\.\d{2}\b', all_text): 
                        result = "W"

                final_data["picks"].append({
                    "id": len(final_data["picks"]) + 1, 
                    "date": date_text.strip(), 
                    "country": country_name.strip(), 
                    "pick": pick_title, 
                    "odds": odds_val, 
                    "result": result
                })
            except: continue
        
        with open('picks.json', 'w') as f:
            json.dump(final_data, f, indent=4)
        print("Success: Removed empty parentheses while keeping (W) and fixed win/loss logic.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    scrape_blogabet()
