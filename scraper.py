import json
import cloudscraper
from bs4 import BeautifulSoup
import re
import time

def scrape_blogabet():
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})
    headers = {"X-Requested-With": "XMLHttpRequest"}
    
    # Nustatome slapuką globaliai, kad sesija išliktų per visas užklausas
    scraper.cookies.update({"ageVerified": "1"})
    
    final_data = {"stats": {"roi": "-", "picks": "-"}, "picks": []}

    try:
        # 1. IŠVALYTI FILTRUS IR GAUTI 10 NAUJAUSIŲ SPĖJIMŲ
        # Sugeneruojame dinaminį laiko žymeklį, kaip tai daro naršyklė (pvz., 1775093281000)
        timestamp = int(time.time() * 1000)
        
        # Naudojame "Clear all" endpoint'ą
        picks_url = f"https://dime.blogabet.com/blog/picks?filters%5Brange%5D%5Bdata1%5D=&filters%5Brange%5D%5Bdata2%5D=&filters%5Btype%5D=0&_={timestamp}"
        picks_res = scraper.get(picks_url, headers=headers)

        # 2. GAUTI ROI IR SPĖJIMŲ SKAIČIŲ TIESIAI IŠ STATISTIKOS PUSLAPIO
        # Siunčiame tuščius filtrų parametrus TIESIAI į statistikos užklausą, 
        # kad serveris priverstinai grąžintų visų laikų (all-time) statistiką (+11% ir 413).
        try:
            stats_url = f"https://dime.blogabet.com/blog/stats?filters%5Brange%5D%5Bdata1%5D=&filters%5Brange%5D%5Bdata2%5D=&filters%5Btype%5D=0&_={timestamp + 1}"
            stats_res = scraper.get(stats_url, headers=headers)
            
            # A metodas: Ieškome JS atnaujinimų AJAX atsakyme
            picks_match = re.search(r'#header-picks[\s\S]*?(?:text|html)\s*\(\s*[\'"]?([+\-0-9.%]+)[\'"]?\s*\)', stats_res.text)
            roi_match = re.search(r'#header-yield[\s\S]*?(?:text|html)\s*\(\s*[\'"]?([+\-0-9.%]+)[\'"]?\s*\)', stats_res.text)
            
            if picks_match: final_data["stats"]["picks"] = picks_match.group(1).strip()
            if roi_match: final_data["stats"]["roi"] = roi_match.group(1).strip()

            # B metodas: Jei JS nerastas, analizuojame HTML statistikos lentelę
            if final_data["stats"]["roi"] in ["-", ""] or final_data["stats"]["picks"] in ["-", ""]:
                stats_soup = BeautifulSoup(stats_res.text, 'html.parser')
                
                roi_elem = stats_soup.find(id="header-yield")
                picks_elem = stats_soup.find(id="header-picks")
                
                if roi_elem: final_data["stats"]["roi"] = roi_elem.get_text(strip=True)
                if picks_elem: final_data["stats"]["picks"] = picks_elem.get_text(strip=True)

                # C metodas: Regex paieška HTML lentelėje
                if final_data["stats"]["roi"] in ["-", ""]:
                    yield_table_match = re.search(r'(?i)Yield[\s\S]{1,150}?(?:>|\s)([+\-]?\d+(?:\.\d+)?\s*%)', stats_res.text)
                    if yield_table_match: 
                        final_data["stats"]["roi"] = yield_table_match.group(1).strip()
                    else:
                        green_yield = re.search(r'(?i)text-green[^>]*>\s*([+]\d+(?:\.\d+)?\s*%)', stats_res.text)
                        if green_yield: final_data["stats"]["roi"] = green_yield.group(1).strip()

                if final_data["stats"]["picks"] in ["-", ""]:
                    picks_table_match = re.search(r'(?i)Picks[\s\S]{1,150}?(?:>|\s)(\d+)(?:<|\s)', stats_res.text)
                    if picks_table_match: 
                        final_data["stats"]["picks"] = picks_table_match.group(1).strip()
        except: pass

        # 3. ANALIZUOTI SPĖJIMUS
        picks_soup = BeautifulSoup(picks_res.text, 'html.parser')
        pick_blocks = picks_soup.find_all('li', class_=re.compile(r'feed-pick'))
        
        seen_titles = set()
        for block in pick_blocks:
            if len(final_data["picks"]) >= 10: break 
            
            try:
                # RUNGTYNĖS IR PASIRINKIMAS
                matchup = block.find('h3').get_text(strip=True) if block.find('h3') else ""
                selection_elem = block.find(class_=re.compile(r'pick-line|pick-name|selection'))
                selection = selection_elem.get_text(strip=True) if selection_elem else matchup
                
                # VALYMAS
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

                # ŠALIS
                country_name = "World"
                for text_elem in block.find_all(['small', 'span', 'div', 'a']):
                    raw_str = text_elem.get_text(" ", strip=True)
                    if "Basketball" in raw_str and "/" in raw_str:
                        parts = [p.strip() for p in raw_str.split('/')]
                        if len(parts) >= 2 and parts[0].upper() == "BASKETBALL":
                            country_name = parts[1]
                            break

                # DATA
                date_text = "-"
                date_container = block.select_one('.feed-date, .date, .time')
                if date_container:
                    date_text = " ".join(date_container.stripped_strings)
                
                if date_text == "-":
                    raw_text = block.get_text(" ")
                    match = re.search(r'(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})', raw_text)
                    if match:
                        date_text = match.group(1)

                # KOEFICIENTAI
                all_text = block.get_text(" ")
                odds_val = "-"
                odds_match = re.search(r'@\s*(\d+\.?\d*)', all_text)
                if odds_match: odds_val = odds_match.group(1)
                
                # REZULTATO NUSTATYMAS
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
        print(f"Sėkmė: Gauta {len(final_data['picks'])} naujausių spėjimų.")
        print(f"Gauta statistika -> ROI: {final_data['stats']['roi']} | Spėjimai: {final_data['stats']['picks']}")

    except Exception as e:
        print(f"Klaida: {e}")

if __name__ == "__main__":
    scrape_blogabet()
