import json
import cloudscraper
from bs4 import BeautifulSoup
import datetime
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
                
                # CLEANING
                clean_text = re.search(r'[^@]*', selection).group(0)
                clean_text = re.sub(r'\(.*?\)', '', clean_text)
                for term in [r'(?i)Spread', r'(?i)Game Lines', r'(?i)Odds', r'(?i)Handicap', r'(?i)Main']:
                    clean_text = re.sub(term, '', clean_text)
                
                # TEAM NAME + ML RULE
                if "MONEY LINE" in selection.upper() or "ML" in selection.upper():
                    team_name = re.sub(r'(?i)Money Line|ML', '', clean_text).strip()
                    if not team_name: team_name = matchup.split('-')[0].split('vs')[0].strip()
                    pick_title = f"{team_name} ML"
                else:
                    pick_title = clean_text.strip()

                if pick_title in seen_titles: continue
                seen_titles.add(pick_title)

                # --- TARGETED DATE FIX ---
                # We only look for the specific 'feed-date' or 'date' class
                date_text = ""
                date_elem = block.find(class_=re.compile(r'feed-date|date'))
                if date_elem:
                    # Get the text but exclude any nested time or extra metadata
                    date_text = date_elem.get_text(" ", strip=True)
                    # If the date is too long (contains time), take only the first 11 characters (DD Mon YYYY)
                    if len(date_text) > 11:
                        date_match = re.search(r'\d{1,2}\s+[A-Za-z]{3}\s+\d{4}', date_text)
                        if date_match:
                            date_text = date_match.group(0)
                
                if not date_text:
                    date_text = str(datetime.date.today())

                # ODDS & RESULT
                all_text = block.get_text(" ")
                odds_val = "-"
                odds_match = re.search(r'@\s*(\d+\.?\d*)', all_text)
                if odds_match: odds_val = odds_match.group(1)
                
                # RESULT ENGINE (Ensuring Red L)
                result = "-"
                # Check for negative profit symbol
                if "-" in all_text and any(x in all_text for x in ["00", "50", "units"]):
                    result = "L"
                elif block.find(class_=re.compile(r'label-danger|text-red|lost|loss')):
                    result = "L"
                elif block.find(class_=re.compile(r'label-success|text-green|win|won')):
                    result = "W"
                
                if result == "-":
                    upper_text = all_text.upper()
                    if "LOST" in upper_text or "LOSS" in upper_text: result = "L"
                    elif "WON" in upper_text or "WIN" in upper_text: result = "W"

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
        print("Success: Fixed dates and results.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    scrape_blogabet()
