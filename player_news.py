import feedparser
from urllib.parse import quote
from datetime import datetime


# Palabras que pueden indicar problemas físicos
PHYSICAL_KEYWORDS = [
    "injury",
    "injured",
    "injuries",
    "medical timeout",
    "medical time-out",
    "medical treatment",
    "physio",
    "physiotherapist",
    "retired",
    "retirement",
    "withdraw",
    "withdrawal",
    "fitness concern",
    "physical problem",
    "hamstring",
    "wrist injury",
    "ankle injury",
    "knee injury",
    "back injury",
    "shoulder injury",
    "illness",
    "sick",
    "cramp",
    "cramps",
    "injured",
    "lesión",
    "lesionado",
    "lesiones",
    "molestias",
    "problema físico",
    "asistencia médica",
    "tiempo médico",
    "abandono",
    "retirada",
]


def search_player_news(player_name, max_results=10):

    queries = [
        f'"{player_name}" tennis injury',
        f'"{player_name}" tennis medical timeout',
        f'"{player_name}" tennis injury OR medical OR retired'
    ]

    articles = []
    seen_titles = set()

    for query in queries:

        url = (
            "https://news.google.com/rss/search?q="
            + quote(query)
            + "&hl=en&gl=US&ceid=US:en"
        )

        feed = feedparser.parse(url)

        for entry in feed.entries:

            title = entry.get("title", "")
            link = entry.get("link", "")
            published = entry.get("published", "")

            key = title.lower()

            if key in seen_titles:
                continue

            seen_titles.add(key)

            text = title.lower()

            physical_alert = any(
                keyword in text
                for keyword in PHYSICAL_KEYWORDS
            )

            articles.append({
                "title": title,
                "link": link,
                "published": published,
                "physical_alert": physical_alert
            })

    return articles[:max_results]


def analyse_physical_status(player_name):

    articles = search_player_news(player_name)

    alerts = [
        article
        for article in articles
        if article["physical_alert"]
    ]

    if len(alerts) >= 3:

        status = "🔴 ALERTA ALTA"

    elif len(alerts) >= 1:

        status = "🟡 REVISAR INFORMACIÓN"

    else:

        status = "🟢 SIN ALERTAS DETECTADAS"

    return {
        "player": player_name,
        "status": status,
        "alerts": alerts,
        "articles": articles
    }