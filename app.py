from flask import Flask, render_template
from flask import request
from scraper import get_sports_events
from scraper import get_sports_data
from scraper import get_sports_venues, get_sports_news

app = Flask(__name__)

@app.route("/")
def home():
    venues = get_sports_venues()
    return render_template("index.html", venues=venues)


@app.route("/venues")
def venues_page():

    venues = get_sports_venues()

    selected_sport = request.args.get("sport")

    if selected_sport:
        venues = [
            v for v in venues
            if v["sport"] == selected_sport
        ]

    return render_template(
        "venues.html",
        venues=venues,
        selected_sport=selected_sport
    )


@app.route("/map")
def map_page():
    venues = get_sports_venues()
    return render_template("map.html", venues=venues)


@app.route("/news")
def news_page():
    news = get_sports_news()
    return render_template("news.html", news=news)


@app.route("/events")
def events_page():

    events = get_sports_events()

    return render_template("events.html", events=events)


@app.route("/sports")
def sports_page():
    
    sports_list = get_sports_data()
    all_events = get_sports_events()
    all_news = get_sports_news()

    
    for s in sports_list:
        hr_name = s["name"].lower()  
        
        
        s["events"] = [
            e for e in all_events 
            if hr_name in e["sport"].lower() or hr_name in e["title"].lower()
        ][:2]  # Uzmi maksimalno 2
        
        
        s["news"] = [
            n for n in all_news 
            if hr_name in n["title"].lower()
        ][:2]  # Uzmi maksimalno 2

    return render_template("sports.html", sports=sports_list)

if __name__ == "__main__":
    app.run()