import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
import time


# =========================================================
# DATUM SPORTSKOG DOGAĐAJA
# =========================================================

def get_event_date(detail_url):

    try:
        response = requests.get(
            detail_url,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=10
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        time_tag = soup.select_one(
            "time.event-single-date-primary"
        )

        if time_tag:

            if time_tag.get("datetime"):

                return time_tag["datetime"].split("T")[0]

            return time_tag.get_text(strip=True)

    except Exception as error:

        print(
            "Greška kod dohvaćanja datuma događaja:",
            error
        )

    return None


# =========================================================
# SPORTSKI OBJEKTI
# =========================================================

def get_sports_venues():

    try:
        with open(
            "venues_cache.json",
            "r",
            encoding="utf-8"
        ) as file:

            venues = json.load(file)

        return venues

    except Exception as error:

        print(
            "Greška kod učitavanja sportskih objekata:",
            error
        )

        return []


# =========================================================
# VREMENSKI UVJETI ZA TRENING
# =========================================================

def get_training_conditions():

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": 45.3271,
        "longitude": 14.4422,
        "current": (
            "temperature_2m,"
            "apparent_temperature,"
            "wind_speed_10m,"
            "precipitation"
        ),
        "timezone": "Europe/Zagreb"
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()
        current = data["current"]

        temperature = current["temperature_2m"]
        feels_like = current["apparent_temperature"]
        wind = current["wind_speed_10m"]
        precipitation = current["precipitation"]

        if precipitation > 0:

            recommendation = (
                "Pada kiša – preporučuje se trening u dvorani"
            )

            status = "bad"

        elif wind > 30:

            recommendation = (
                "Jak vjetar – potreban je oprez na otvorenom"
            )

            status = "warning"

        elif temperature > 30:

            recommendation = (
                "Vrlo je toplo – treniraj lakše i pij dovoljno vode"
            )

            status = "warning"

        elif temperature < 5:

            recommendation = (
                "Hladno je – dobro se zagrij prije treninga"
            )

            status = "warning"

        else:

            recommendation = (
                "Dobri uvjeti za trening na otvorenom"
            )

            status = "good"

        return {
            "temperature": temperature,
            "feels_like": feels_like,
            "wind": wind,
            "precipitation": precipitation,
            "recommendation": recommendation,
            "status": status,
            "updated": current.get("time", ""),
            "error": False
        }

    except Exception as error:

        print(
            "Greška kod dohvaćanja vremena:",
            error
        )

        return {
            "temperature": "--",
            "feels_like": "--",
            "wind": "--",
            "precipitation": "--",
            "recommendation": (
                "Trenutačno nije moguće dohvatiti vremenske podatke"
            ),
            "status": "bad",
            "updated": "",
            "error": True
        }
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

        #  DOHVAĆANJE DATUMA 
        date = "datum"

       
        if link != "#":
            detail_date = get_event_date(link)
            if detail_date and detail_date != "datum":
                date = detail_date

       
        if date == "datum":
            time_tag = card.find("time")
            if time_tag:
                date = " ".join(time_tag.stripped_strings)
            else:
                date_tag = card.select_one(".date, .event-date, .meta-date")
                if date_tag:
                    date = date_tag.get_text(" ", strip=True)
                else:
                    
                    card_text = card.get_text(" ", strip=True)
                    if "Datum:" in card_text:
                        try:
                           
                            date_part = card_text.split("Datum:")[1].split("\n")[0].strip()
                            
                            if "Lokacija" in date_part:
                                date_part = date_part.split("Lokacija")[0].strip()
                            if date_part:
                                date = date_part
                        except Exception:
                            pass

       
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
