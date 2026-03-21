import json
import datetime

# This is the placeholder structure. Next, we will add BeautifulSoup 
# here to pull live data from https://dime.blogabet.com
def scrape_blogabet():
    print("Running scraper...")
    # Dummy data to test the automated pipeline
    new_picks = [
        {"id": 1, "date": str(datetime.date.today()), "pick": "Test Pick 1", "odds": "1.95", "result": "W"},
        {"id": 2, "date": "2026-03-21", "pick": "Test Pick 2", "odds": "1.85", "result": "L"},
        {"id": 3, "date": "2026-03-20", "pick": "Test Pick 3", "odds": "2.00", "result": "-"},
        {"id": 4, "date": "2026-03-19", "pick": "Test Pick 4", "odds": "1.90", "result": "W"},
        {"id": 5, "date": "2026-03-18", "pick": "Test Pick 5", "odds": "1.90", "result": "W"}
    ]
    
    with open('picks.json', 'w') as f:
        json.dump(new_picks, f, indent=4)
        
if __name__ == "__main__":
    scrape_blogabet()
