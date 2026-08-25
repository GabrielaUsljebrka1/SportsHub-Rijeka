from flask import Flask, render_template, request

from scraper import get_sports_events
from scraper import get_sports_data
from scraper import get_sports_venues
from scraper import get_sports_news
from scraper import get_training_conditions


app = Flask(__name__)


@app.route("/")
def home():

    return render_template("index.html")


@app.route("/venues")
def venues_page():

    venues = get_sports_venues()
    selected_sport = request.args.get("sport")

    if selected_sport:
        venues = [
            venue for venue in venues
            if venue["sport"] == selected_sport
        ]

    return render_template(
        "venues.html",
        venues=venues,
        selected_sport=selected_sport
    )


@app.route("/conditions")
def conditions_page():

    conditions = get_training_conditions()

    return render_template(
        "conditions.html",
        conditions=conditions
    )


@app.route("/news")
def news_page():

    news = get_sports_news()

    return render_template(
        "news.html",
        news=news
    )


@app.route("/events")
def events_page():

    events = get_sports_events()

    return render_template(
        "events.html",
        events=events
    )


@app.route("/sports")
def sports_page():

    sports_list = get_sports_data()
    all_events = get_sports_events()
    all_news = get_sports_news()

    for sport in sports_list:

        hr_name = sport["name"].lower()

        sport["events"] = [
            event for event in all_events
            if (
                hr_name in event["sport"].lower()
                or hr_name in event["title"].lower()
            )
        ][:2]

        sport["news"] = [
            news for news in all_news
            if hr_name in news["title"].lower()
        ][:2]

    return render_template(
        "sports.html",
        sports=sports_list
    )


if __name__ == "__main__":
    app.run()