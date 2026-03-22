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
            if len(new_picks) >= 30: break 
            
            try:
                # 1. GET RAW DATA
                matchup = block.find('h3').get_text(strip=True) if block.find('h3') else ""
                selection_elem = block.find(class_=re.compile(r'pick-line|pick-name|selection'))
                selection = selection_elem.get_text(strip=True) if selection_elem else matchup
                
                # 2. THE CLEANING ENGINE
                # Remove everything after '@' (the odds)
                clean_text = re.search(r'[^@]*', selection).group(0)
                # Remove parentheses and content inside
                clean_text = re.sub(r'\(.*?\)', '', clean_text)
                # Remove jargon labels
                unwanted = [r'(?i)Spread', r'(?i)Game Lines', r'(?i)Odds', r'(?i)Handicap', r'(?i)Main']
                for term in unwanted:
                    clean_text = re.sub(term, '', clean_text)
                
                # 3. APPLY ML SUFFIX RULE (Team Name + ML)
                if "MONEY LINE" in selection.upper() or "ML" in selection.upper():
                    # Strip "Money Line" and "ML" out to get just the team name
                    team_name = re.sub(r'(?i)Money Line|ML', '', clean_text).strip()
                    # If cleaning made it empty, fallback to the first team in the matchup
                    if not team_name:
                        team_name = matchup.split('-')[0].split('vs')[0].strip()
                    # FINAL FORMAT: Team Name ML
                    pick_title = f"{team_name} ML"
                else:
                    # Keep as Team Name + Handicap (e.g., Fribourg -34.5)
                    pick_title = clean_text.strip()

                # Deduplicate based on final formatted title
                if pick_title in seen_titles: continue
                seen_titles.add(pick_title)

                # 4. DATE, ODDS, & RESULT
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
        print(f"Successfully saved {len(new_picks)} picks in Team + ML format.")
        
    except Exception as e:
        print(f"Critical Scraper Error: {e}")

if __name__ == "__main__":
    scrape_blogabet()
