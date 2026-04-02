import json
import cloudscraper
from bs4 import BeautifulSoup
import re
import time

def scrape_blogabet():
    main_url = "https://dime.blogabet.com"
    
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})
    headers = {"X-Requested-With": "XMLHttpRequest"}
    cookies = {"ageVerified": "1"}
    
    final_data = {"stats": {"roi": "+18.4%", "picks": "372"}, "picks": []}

    try:
        # 1. CLEAR FILTERS & GET THE FRESH 10 PICKS
        # Generate a dynamic timestamp just like the browser does (e.g., 1775093281000)
        timestamp = int(time.time() * 1000)
        
        # We use the exact "Clear all" endpoint and parse ITS response directly.
        # Calling this URL first resets the server-side filters for our current session.
        picks_url = f"https://dime.blogabet.com/blog/picks?filters%5Brange%5D%5Bdata1%5D=&filters%5Brange%5D%5Bdata2%5D=&filters%5Btype%5D=0&_={timestamp}"
        picks_res = scraper.get(picks_url, headers=headers, cookies=cookies)

        # 2. GET ROI AND PICKS FOR THE CLEARED STATE
        try:
            # When filters are cleared, Blogabet returns inline JavaScript to update the header stats.
            # We intercept this JS to get the true "Cleared" lifetime stats (e.g. 413 and +11%).
            picks_match = re.search(r"\$\(\s*['\"]#header-picks['\"]\s*\)\.(?:text|html)\(\s*['\"]([^'\"]+)['\"]\s*\)", picks_res.text)
            roi_match = re.search(r"\$\(\s*['\"]#header-yield['\"]\s*\)\.(?:text|html)\(\s*['\"]([^'\"]+)['\"]\s*\)", picks_res.text)
            
            if picks_match and roi_match:
                final_data["stats"]["picks"] = picks_match.group(1)
                final_data["stats"]["roi"] = roi_match.group(1)
            else:
                # Fallback: Scrape the main page directly if the JS isn't found
                main_res = scraper.get(main_url, cookies=cookies)
                main_soup = BeautifulSoup(main_res.text, 'html.parser')
                
                picks_elem = main_soup.find(id="header-picks")
                roi_elem = main_soup.find(id="header-yield")
                
                if picks_elem: final_data["stats"]["picks"] = picks_elem.get_text(strip=True)
                if roi_elem: final_data["stats"]["roi"] = roi_elem.get_text(strip=True)
        except: pass

        # 3. PARSE THE PICKS
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
                
                # RESULT DETECTION
                result = "PENDING"
                
                labels = block.find_all(class_=re.compile(r'\b(label-success|label-danger|label-warning)\b'))
                for label in labels:
                    lbl_text = label.get_text(strip=True).upper()
                    if lbl_text in ["WIN", "WON", "W"]:
                        result = "W"
                    elif lbl_text in ["LOSS", "LOST", "L"]:
                        result = "L"
                    elif lbl_text in ["VOID", "DRAW", "REFUND", "HALF WON", "HALF LOST"]:
                        result = lbl_text
                
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
        print(f"Success: Fetched {len(final_data['picks'])} recent picks and updated global stats.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    scrape_blogabet()
