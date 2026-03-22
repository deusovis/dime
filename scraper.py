import json
import cloudscraper
from bs4 import BeautifulSoup
import datetime
import re

def scrape_blogabet():
    # Target URLs
    main_url = "https://dime.blogabet.com"
    picks_url = "https://dime.blogabet.com/blog/picks"
    
    # Initialize the scraper to bypass Cloudflare security
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})
    headers = {"X-Requested-With": "XMLHttpRequest"}
    cookies = {"ageVerified": "1"}
    
    # Default data structure
    final_data = {
        "stats": {"roi": "+0%", "units": "0.0"},
        "picks": []
    }

    try:
        # --- STEP 1: SCRAPE ROI AND UNITS FROM MAIN PROFILE ---
        print("Connecting to main profile for stats...")
        main_res = scraper.get(main_url, cookies=cookies)
        main_soup = BeautifulSoup(main_res.text, 'html.parser')
        
        profit_elem = main_soup.find(id="header-profit")
        roi_elem = main_soup.find(id="header-yield")
        
        if profit_elem:
            final_data["stats"]["units"] = profit_elem.get_text(strip=True)
        if roi_elem:
            final_data["stats"]["roi"] = roi_elem.get_text(strip=True)
            
        print(f"Stats Updated: ROI ({final_data['stats']['roi']}) Units ({final_data['stats']['units']})")

        # --- STEP 2: SCRAPE LAST 10 PICKS ---
        print("Fetching latest picks...")
        picks_res = scraper.get(picks_url, headers=headers, cookies=cookies)
        picks_soup = BeautifulSoup(picks_res.text, 'html.parser')
        
        # Blogabet uses <li> tags with 'feed-pick' for each entry
        pick_blocks = picks_soup.find_all('li', class_=re.compile(r'feed-pick'))
        
        seen_titles = set()
        for block in pick_blocks:
            if len(final_data["picks"]) >= 10: 
                break # Stop at exactly 10 picks
            
            try:
                # 1. Capture Raw Selection & Matchup
                matchup = block.find('h3').get_text(strip=True) if block.find('h3') else ""
                selection_elem = block.find(class_=re.compile(r'pick-line|pick-name|selection'))
                selection = selection_elem.get_text(strip=True) if selection_elem else matchup
                
                # 2. Advanced Cleaning (Remove Odds @, Parentheses, and Jargon)
                clean_text = re.search(r'[^@]*', selection).group(0)
                clean_text = re.sub(r'\(.*?\)', '', clean_text)
                
                unwanted_terms = [r'(?i)Spread', r'(?i)Game Lines', r'(?i)Odds', r'(?i)Handicap', r'(?i)Main']
                for term in unwanted_terms:
                    clean_text = re.sub(term, '', clean_text)
                
                # 3. Team Name + ML Suffix Logic
                if "MONEY LINE" in selection.upper() or "ML" in selection.upper():
                    team_name = re.sub(r'(?i)Money Line|ML', '', clean_text).strip()
                    if not team_name: # Fallback to matchup if selection text is just "Money Line"
                        team_name = matchup.split('-')[0].split('vs')[0].strip()
                    pick_title = f"{team_name} ML"
                else:
                    pick_title = clean_text.strip()

                # Duplicate Prevention
                if pick_title in seen_titles: continue
                seen_titles.add(pick_title)

                # 4. Capture Correct Blogabet Date (Joining Spans)
                date_container = block.find(class_=re.compile(r'feed-date|date|time'))
                if date_container:
                    # Joins "21", "Mar", "2026" into "21 Mar 2026"
                    date_text = " ".join(date_container.stripped_strings)
                else:
                    date_text = str(datetime.date.today())

                # 5. Capture Odds
                all_text = block.get_text(" ")
                odds_val = "-"
                odds_match = re.search(r'@\s*(\d+\.?\d*)', all_text)
                if odds_match:
                    odds_val = odds_match.group(1)
                
                # 6. Aggressive Result Detection (Fixing the Grey "-" issue)
                result = "-"
                # Check A: Check for negative/positive profit symbols in text
                profit_match = re.search(r'([+-])\d+\.\d+', all_text)
                if profit_match:
                    result = "W" if profit_match.group(1) == "+" else "L"
                
                # Check B: CSS Classes
                if result == "-":
                    if block.find(class_=re.compile(r'label-success|text-green|win|won')):
                        result = "W"
                    elif block.find(class_=re.compile(r'label-danger|text-red|lose|lost|lost-pick')):
                        result = "L"
                
                # Check C: Keyword Search
                if result == "-":
                    upper_text = all_text.upper()
                    if any(x in upper_text for x in ["WON", "WIN"]):
                        result = "W"
                    elif any(x in upper_text for x in ["LOST", "LOSE", "LOSS"]):
                        result = "L"

                final_data["picks"].append({
                    "id": len(final_data["picks"]) + 1,
                    "date": date_text.strip(),
                    "pick": pick_title,
                    "odds": odds_val,
                    "result": result
                })
                
            except Exception as e:
                print(f"Error parsing individual pick: {e}")
                continue
        
        # Save to picks.json
        with open('picks.json', 'w') as f:
            json.dump(final_data, f, indent=4)
            
        print(f"Successfully saved {len(final_data['picks'])} picks and live stats.")

    except Exception as e:
        print(f"Critical Scraper Error: {e}")

if __name__ == "__main__":
    scrape_blogabet()
