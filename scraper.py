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
        # CRITICAL FIX: Always use the new BeautifulSoup object for the picks
        picks_soup = BeautifulSoup(picks_res.text, 'html.parser')
        pick_blocks = picks_soup.find_all('li', class_=re.compile(r'feed-pick'))
        
        seen_titles = set()
        for block in pick_blocks:
            if len(final_data["picks"]) >= 10: break 
            
            try:
                matchup = block.find('h3').get_text(strip=True) if block.find('h3') else ""
                selection_elem = block.find(class_=re.compile(r'pick-line|pick-name|selection'))
                selection = selection_elem.get_text(strip=True) if selection_elem else matchup
                
                # CLEANING & ML FORMATTING
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

                # --- NEW BULLETPROOF DATE LOGIC ---
                date_text = ""
                # Search for any div or span with 'date' in the class
                date_elem = block.find(class_=re.compile(r'feed-date|date|time'))
                if date_elem:
                    date_text = " ".join(date_elem.stripped_strings)
                
                # If class-based search fails, scan raw text for date patterns (e.g., 21 Mar)
                if not date_text or len(date_text) < 3:
                    all_text_content = block.get_text(" ")
                    # Regex looks for: 1-2 digits, then 3 letters (month), then optional 4 digits (year)
                    match = re.search(r'\d{1,2}\s+[A-Za-z]{3}(\s+\d{4})?', all_text_content)
                    date_text = match.group(0) if match else str(datetime.date.today())

                # ODDS
                all_text = block.get_text(" ")
                odds_val = "-"
                odds_match = re.search(r'@\s*(\d+\.?\d*)', all_text)
                if odds_match: odds_val = odds_match.group(1)
                
                # RESULT ENGINE (Solid Red Fix)
                result = "-"
                if block.find(class_=re.compile(r'label-danger|text-red|lost|loss|lost-pick')):
                    result = "L"
                elif block.find(class_=re.compile(r'label-success|text-green|win|won|win-pick')):
                    result = "W"
                
                if result == "-":
                    upper_text = all_text.upper()
                    if any(x in upper_text for x in ["LOST", "LOSS", "LOSE", "-1.00", "-0.50"]):
                        result = "L"
                    elif any(x in upper_text for x in ["WON", "WIN", "PROFIT"]):
                        result = "W"

                final_data["picks"].append({
                    "id": len(final_data["picks"]) + 1, 
                    "date": date_text.strip(), 
                    "pick": pick_title, 
                    "odds": odds_val, 
                    "result": result
                })
            except Exception as e:
                print(f"Skipping pick due to internal error: {e}")
                continue
        
        with open('picks.json', 'w') as f:
            json.dump(final_data, f, indent=4)
        print(f"Scrape successful. Saved {len(final_data['picks'])} picks.")

    except Exception as e:
        print(f"Scraper failed completely: {e}")

if __name__ == "__main__":
    scrape_blogabet()
