import json
import cloudscraper
from bs4 import BeautifulSoup
import re

def scrape_blogabet():
    main_url = "https://dime.blogabet.com"
    picks_url = "https://dime.blogabet.com"
    
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})
    headers = {"X-Requested-With": "XMLHttpRequest"}
    cookies = {"ageVerified": "1"}
    
    # UPDATED: Swapped 'units' for 'picks' with a default value
    final_data = {"stats": {"roi": "+18.4%", "picks": "372"}, "picks": []}

    try:
        # 1. GET ROI AND PICKS FROM HEADER
        try:
            main_res = scraper.get(main_url, cookies=cookies)
            main_soup = BeautifulSoup(main_res.text, 'html.parser')
            
            # UPDATED: Targeting the header-picks ID instead of header-profit
            picks_elem = main_soup.find(id="header-picks")
            roi_elem = main_soup.find(id="header-yield")
            
            if picks_elem: final_data["stats"]["picks"] = picks_elem.get_text(strip=True)
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
                
                # CLEANING
                clean_text = re.search(r'[^@]*', selection).group(0)
                for term in [r'(?i)Spread', r'(?i)Game Lines', r'(?i)Odds', r'(?i)Handicap', r'(?i)Main']:
                    clean_text = re.sub(term, '', clean_text)
                
                clean_text = re.sub(r'\(\s*\)', '', clean_text)
                
                if "MONEY LINE" in selection.upper() or "ML" in selection.upper():
                    team_name = re.sub(r'(?i)Money Line|ML', '', clean_text).strip()
                    team_name = team_name.strip(" -")
                    team_name = re.sub(r'\s+', ' ', team_name).strip()
                    
                    if not team_name: team_name = matchup.split('-')[0].split('vs')[0].strip()
                    pick_title = f"{team_name} ML"
                else:
                    pick_title = re.sub(r'\s+', ' ', clean_text).strip()

                if pick_title in seen_titles: continue
                seen_titles.add(pick_title)

                # COUNTRY
                country_name = "World"
                for text_elem in block.find_all(['small', 'span', 'div', 'a']):
                    raw_str = text_elem.get_text(" ", strip=True)
                    if "Basketball" in raw_str and "/" in raw_str:
                        parts = [p.strip() for p in raw_str.split('/')]
                        if len(parts) >= 2 and parts[0].upper() == "BASKETBALL":
                            country_name = parts[1]
                            break

                # DATE
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
                
                # --- BULLETPROOF RESULT DETECTION ---
                result = "PENDING"
                
                # Target exact label badges only (ignores 'text-green' verified checkmarks)
                labels = block.find_all(class_=re.compile(r'\b(label-success|label-danger|label-warning)\b'))
                for label in labels:
                    lbl_text = label.get_text(strip=True).upper()
                    if lbl_text in ["WIN", "WON", "W"]:
                        result = "W"
                    elif lbl_text in ["LOSS", "LOST", "L"]:
                        result = "L"
                    elif lbl_text in ["VOID", "DRAW", "REFUND", "HALF WON", "HALF LOST"]:
                        result = lbl_text
                
                # Fallback: strictly check profit/loss numbers (+ units or - units)
                if result == "PENDING":
                    if re.search(r'\+\d+\.\d{2}\b', all_text):
                        result = "W"
                    elif re.search(r'-\d+\.\d{2}\b', all_text):
                        result = "L"

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
        print("Success: Bulletproof result logic applied.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    scrape_blogabet()
