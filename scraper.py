import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
import time

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

SPORT_TRANSLATIONS = {
    "soccer": "Nogomet",
    "basketball": "Košarka",
    "tennis": "Tenis",
    "swimming": "Plivanje",
    "swimming_pool": "Plivanje",
    "fitness": "Fitness",
    "handball": "Rukomet",
    "volleyball": "Odbojka",
    "table_tennis": "Stolni tenis",
    "cycling": "Biciklizam",
    "climbing": "Penjanje",
    "futsal": "Futsal",
    "athletics": "Atletika",
    "running": "Trčanje",
    "sailing": "Jedrenje",
    "motor": "Moto sport",
    "scuba_diving": "Ronjenje",
    "paragliding": "Paragliding",
    "shooting": "Streljaštvo",
    "yoga": "Yoga",
    "beachvolleyball": "Odbojka na pijesku"
}


def get_event_date(detail_url):
    try:
        r = requests.get(detail_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        time_tag = soup.select_one("time.event-single-date-primary")

        if time_tag:
            # 1. najtočnije (ISO datum)
            if time_tag.get("datetime"):
                return time_tag["datetime"].split("T")[0]

            # 2. fallback tekst
            return time_tag.get_text(strip=True)

    except Exception as e:
        print("Date scrape error:", e)

    return None

 #OBJEKTI - VENUES 
def get_sports_venues():
    cache_file = "venues_cache.json"
    cache_duration = 60 * 60 * 24  # 24 sata

    if os.path.exists(cache_file):
        file_age = time.time() - os.path.getmtime(cache_file)

        if file_age < cache_duration:
            with open(cache_file, "r", encoding="utf-8") as file:
                return json.load(file)

    query = """
    [out:json][timeout:25];
    area["name"="Rijeka"]["boundary"="administrative"]->.searchArea;

    (
      node["leisure"~"sports_centre|pitch|stadium|swimming_pool"](area.searchArea);
      way["leisure"~"sports_centre|pitch|stadium|swimming_pool"](area.searchArea);
      relation["leisure"~"sports_centre|pitch|stadium|swimming_pool"](area.searchArea);

      node["amenity"~"fitness_centre|swimming_pool"](area.searchArea);
      way["amenity"~"fitness_centre|swimming_pool"](area.searchArea);
      relation["amenity"~"fitness_centre|swimming_pool"](area.searchArea);

      node["sport"](area.searchArea);
      way["sport"](area.searchArea);
      relation["sport"](area.searchArea);
    );

    out center tags;
    """

    try:
        response = requests.get(
            OVERPASS_URL,
            params={"data": query},
            headers={"User-Agent": "SportsHubRijeka/1.0"},
            timeout=30
        )

        response.raise_for_status()
        data = response.json()

    except Exception as error:
        print("Greška kod dohvaćanja sportskih objekata:", error)

        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as file:
                return json.load(file)

        return []

    venues = []

    for element in data.get("elements", []):
        tags = element.get("tags", {})

        name = tags.get("name")
        if not name:
            continue

        lat = element.get("lat") or element.get("center", {}).get("lat")
        lon = element.get("lon") or element.get("center", {}).get("lon")

        if not lat or not lon:
            continue

        sport = (
            tags.get("sport")
            or tags.get("leisure")
            or tags.get("amenity")
            or "unknown"
        )

        sport = str(sport).split(";")[0].lower()

        venues.append({
            "name": name,
            "sport": sport,
            "sport_hr": SPORT_TRANSLATIONS.get(sport, "Ostalo"),
            "lat": lat,
            "lon": lon,
            "address": tags.get("addr:street", ""),
            "website": tags.get("website", ""),
            "source": "OpenStreetMap"
        })

    with open(cache_file, "w", encoding="utf-8") as file:
        json.dump(venues, file, ensure_ascii=False, indent=4)

    return venues
# DOGAĐAJI - EVENTS

EVENTS_URL = "https://www.dogadanja.com/sport/"

def get_sports_events():
    try:
        r = requests.get(
            EVENTS_URL,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        r.raise_for_status()
    except Exception as e:
        print("Error loading events:", e)
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    events = []
    cards = soup.select("article")

    for card in cards:
        # NASLOV
        title_tag = card.find("h2") or card.find("h3")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)

        # LINK
        link = "#"
        a_tag = card.find("a", href=True)
        if a_tag:
            link = a_tag["href"]
            if not link.startswith("http"):
                link = "https://www.dogadanja.com" + link

        # --- DOHVAĆANJE DATUMA ---
        date = "datum"

        # 1. Pokušaj iz detaljne stranice (najtočnije - ISO format sa slike 1)
        if link != "#":
            detail_date = get_event_date(link)
            if detail_date and detail_date != "datum":
                date = detail_date

        # 2. Fallback iz same kartice ako detaljna stranica nije dostupna
        if date == "datum":
            time_tag = card.find("time")
            if time_tag:
                date = " ".join(time_tag.stripped_strings)
            else:
                date_tag = card.select_one(".date, .event-date, .meta-date")
                if date_tag:
                    date = date_tag.get_text(" ", strip=True)
                else:
                    # Dodatni fallback za tekstualni format sa slike 2 ("Datum: 13.6.2026.")
                    card_text = card.get_text(" ", strip=True)
                    if "Datum:" in card_text:
                        try:
                            # Izvlači sve nakon riječi "Datum:" do kraja te linije/rečenice
                            date_part = card_text.split("Datum:")[1].split("\n")[0].strip()
                            # Čišćenje ako se uhvati previše teksta (npr. Lokacija)
                            if "Lokacija" in date_part:
                                date_part = date_part.split("Lokacija")[0].strip()
                            if date_part:
                                date = date_part
                        except Exception:
                            pass

        # LOKACIJA
        location = "Rijeka"
        location_tag = card.find(
            class_=lambda x: x and "location" in x.lower()
        )
        if location_tag:
            location = location_tag.get_text(strip=True)

        # SPORT
        sport = "Ostalo"
        lower = title.lower()
        if "pliva" in lower:
            sport = "Plivanje"
        elif "nogomet" in lower or "liga" in lower:
            sport = "Nogomet"
        elif "koš" in lower:
            sport = "Košarka"
        elif "vaterpolo" in lower:
            sport = "Vaterpolo"
        elif "tenis" in lower:
            sport = "Tenis"

        events.append({
            "title": title,
            "date": date,
            "location": location,
            "sport": sport,
            "link": link
        })

        if len(events) >= 12:
            break

    return events


# VIJESTI - NEWS
def get_sports_news():

    news = []
    
    try:
        
        url = "https://sportcom.hr/regionalni-sport"
        
        r = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        articles = soup.select("h2 a, h3 a")
        
        count = 0
        
        for a in articles:
            
            title = a.get_text(strip=True)
            link = a.get("href")
            
            if not title or not link:
                continue
            
            if not link.startswith("http"):
                link = "https://sportcom.hr" + link
                
            image = ""
            
            parent = a.parent
            
            img_tag = parent.find("img") if parent else None
            
            if img_tag:
                
                image = (
                    img_tag.get("src")
                    or img_tag.get("data-src")
                    or ""
                )
                
            if image and image.startswith("/"):
                image = "https://sportcom.hr" + image
            
            timestamp = int(datetime.now().timestamp()) - (count * 60)
            
            news.append({
                "title": title,
                "link": link,
                "image": image,
                "source_name": "SportCom",
                "timestamp": timestamp
            })
            
            count += 1
            
            if count >= 8:
                break
            
    except Exception as e:
        print("SportCom error: ", e)
        
    news.sort(
        key=lambda x: x["timestamp"],
        reverse=True
    )
    
    return news

#SPORTOVI - SPORTS
def get_sports_data():

    venues = get_sports_venues()
    events = get_sports_events()
    news = get_sports_news()

    sports_count = {}

    for v in venues:

        raw = v["sport"]
        hr = v["sport_hr"]

        if raw not in sports_count:

            sports_count[raw] = {
                "name": hr,
                "count": 0
            }

        sports_count[raw]["count"] += 1

    sports = []

    for raw_name, data in sports_count.items():

        sport_name = data["name"]

        sport_events = [
            e for e in events
            if e["sport"].lower() == sport_name.lower()
        ]

        sport_news = [
            n for n in news
            if sport_name.lower() in n["title"].lower()
        ]

        sports.append({
            "name": sport_name,
            "count": data["count"],
            "raw": raw_name,
            "events": sport_events[:3],
            "news": sport_news[:3]
        })

    sports.sort(key=lambda x: x["count"], reverse=True)

    return sports


#KARTA - MAP