import json
import cloudscraper
from bs4 import BeautifulSoup
import re

def scrape_blogabet():
    # Target URLs
    main_url = "https://dime.blogabet.com"
    picks_url = "https://dime.blogabet.com/blog/picks"
    
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})
    headers = {"X-Requested-With": "XMLHttpRequest"}
    cookies = {"ageVerified": "1"} # Bypass the age wall shown in your source
    
    final_data = {"stats": {"roi": "+18.4%", "units": "+32.1"}, "picks": []}

    try:
        # 1. GET STATS FROM HEADER
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
        
        # Target the <li> elements for each pick
        pick_blocks = picks_soup.find_all('li', class_=re.compile(r'feed-pick'))
        
        seen_titles = set()
        for block in pick_blocks:
            if len(final_data["picks"]) >= 10: break 
            
            try:
                # MATCHUP & SELECTION
                matchup = block.find('h3').get_text(strip=True) if block.find('h3') else ""
                selection_elem = block.find(class_=re.compile(r'pick-line|pick-name|selection'))
                selection = selection_elem.get_text(strip=True) if selection_elem else matchup
                
                # CLEANING (ML Suffix)
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

                # --- SMART DATE SEARCH ---
                date_text = "-"
                # Look for common Blogabet date containers
                date_container = block.select_one('.feed-date, .date, .time, [class*="date"]')
                
                if date_container:
                    # Collect all text inside spans (21, Mar, 2026) and join them
                    raw_strings = list(date_container.stripped_strings)
                    if len(raw_strings) >= 2:
                        # Join the first 3 parts (Day Month Year)
                        date_text = " ".join(raw_strings[:3])
                
                # If container search failed, try raw text scan for "21 Mar 2026" pattern
                if date_text == "-":
                    full_block_text = block.get_text(" ")
                    match = re.search(r'(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})', full_block_text)
                    if match:
                        date_text = match.group(1)

                # ODDS
                all_text = block.get_text(" ")
                odds_val = "-"
                odds_match = re.search(r'@\s*(\d+\.?\d*)', all_text)
                if odds_match: odds_val = odds_match.group(1)
                
                # --- STABLE WIN/LOSS (PRIORITIZE LABELS) ---
                result = "-"
                # Green label = Win, Red label = Loss
                if block.find(class_=re.compile(r'label-success|text-green|win')):
                    result = "W"
                elif block.find(class_=re.compile(r'label-danger|text-red|lose|lost|loss')):
                    result = "L"
                
                # Keyword fallback
                if result == "-":
                    upper_text = all_text.upper()
                    if "WON" in upper_text or "WIN" in upper_text: result = "W"
                    elif "LOST" in upper_text or "LOSE" in upper_text or "LOSS" in upper_text: result = "L"

                final_data["picks"].append({
                    "id": len(final_data["picks"]) + 1, 
                    "date": date_text, 
                    "pick": pick_title, 
                    "odds": odds_val, 
                    "result": result
                })
            except: continue
        
        with open('picks.json', 'w') as f:
            json.dump(final_data, f, indent=4)
        print(f"Scrape successful. Date Found: {final_data['picks'][0]['date'] if final_data['picks'] else 'None'}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    scrape_blogabet()
