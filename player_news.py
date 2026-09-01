import feedparser
from urllib.parse import quote, urlparse
from datetime import datetime, timezone


# =========================================================
# FUENTES PERMITIDAS
# =========================================================

TRUSTED_SOURCES = {
    "atptour.com": "ATP Tour",
    "reuters.com": "Reuters",
    "bbc.com": "BBC Sport",
    "bbc.co.uk": "BBC Sport",
    "apnews.com": "Associated Press",
    "ap.org": "Associated Press",
}


# =========================================================
# PALABRAS DE ALERTA FÍSICA
# =========================================================

HIGH_RISK_KEYWORDS = [
    "retired",
    "retirement",
    "withdraw",
    "withdrawal",
    "withdraws",
    "withdrew",
    "ruled out",
    "surgery",
    "undergoes surgery",
    "medical timeout",
    "medical time-out",
    "medical treatment",
    "injury forces",
    "forced to retire",
    "forced to withdraw",
    "retirada",
    "abandono",
    "se retira",
    "cirugía",
    "operación",
]


MEDIUM_RISK_KEYWORDS = [
    "injury",
    "injured",
    "pain",
    "fitness concern",
    "physical problem",
    "physio",
    "physiotherapist",
    "treatment",
    "cramp",
    "cramps",
    "hamstring",
    "wrist",
    "ankle",
    "knee",
    "back problem",
    "back pain",
    "shoulder",
    "illness",
    "sick",
    "fitness",
    "molestia",
    "dolor",
    "lesión",
    "lesionado",
    "problema físico",
]


RECOVERY_KEYWORDS = [
    "returned from injury",
    "returns from injury",
    "back from injury",
    "recovered",
    "fully fit",
    "fit again",
    "recovery",
    "returns after injury",
    "regresa tras lesión",
    "recuperado",
    "vuelve tras lesión",
]


# =========================================================
# COMPROBAR SI EL DOMINIO ES UNA FUENTE PERMITIDA
# =========================================================

def get_source_name(url):

    try:
        domain = urlparse(url).netloc.lower()

        domain = domain.replace("www.", "")

        for allowed_domain, source_name in TRUSTED_SOURCES.items():

            if domain == allowed_domain or domain.endswith("." + allowed_domain):

                return source_name

    except Exception:
        pass

    return None


# =========================================================
# COMPROBAR QUE LA NOTICIA ES REALMENTE DEL JUGADOR
# =========================================================

def is_player_match(text, player_name):

    text = text.lower()

    player_name = player_name.lower().strip()

    name_parts = player_name.split()

    # Deben aparecer nombre y apellido cuando hay más de una palabra
    if len(name_parts) >= 2:

        first_name = name_parts[0]
        last_name = name_parts[-1]

        return first_name in text and last_name in text

    # Para nombres de una sola palabra
    return player_name in text


# =========================================================
# BUSCAR NOTICIAS SOLO EN FUENTES FIABLES
# =========================================================

def search_player_news(player_name, max_results=15):

    queries = [
        f'"{player_name}" tennis injury',
        f'"{player_name}" tennis retired',
        f'"{player_name}" tennis withdrawal',
        f'"{player_name}" tennis medical timeout',
        f'"{player_name}" tennis fitness',
    ]

    articles = []

    seen_urls = set()
    seen_titles = set()

    for query in queries:

        url = (
            "https://news.google.com/rss/search?q="
            + quote(query)
            + "&hl=en&gl=US&ceid=US:en"
        )

        try:
            feed = feedparser.parse(url)

        except Exception:

            continue


        for entry in feed.entries:

            title = entry.get("title", "").strip()

            link = entry.get("link", "").strip()

            published = entry.get("published", "").strip()

            if not title or not link:

                continue


            # -------------------------------------------------
            # COMPROBAR QUE LA NOTICIA ES DEL JUGADOR
            # -------------------------------------------------

            if not is_player_match(title, player_name):

                continue


            # -------------------------------------------------
            # OBTENER LA URL FINAL
            # -------------------------------------------------

            # Obtener la fuente indicada por Google News
            source_name = None

            source_info = entry.get("source", {})

            if source_info:
                source_url = source_info.get("href", "")
                source_name = get_source_name(source_url)

            # Si no conseguimos identificar una fuente fiable,
            # descartamos la noticia
            if source_name is None:
                continue
      

            # -------------------------------------------------
            # EVITAR DUPLICADOS
            # -------------------------------------------------

            title_key = title.lower()

            if link in seen_urls:

                continue

            if title_key in seen_titles:

                continue


            seen_urls.add(link)

            seen_titles.add(title_key)


            articles.append({
                "title": title,
                "link": link,
                "published": published,
                "source": source_name
            })


    return articles[:max_results]


# =========================================================
# ANALIZAR ESTADO FÍSICO
# =========================================================

def analyse_physical_status(player_name):

    articles = search_player_news(player_name)

    score = 0

    high_alerts = []
    medium_alerts = []
    recovery_alerts = []

    now = datetime.now(timezone.utc)


    # =====================================================
    # CALCULAR CUÁNTOS DÍAS TIENE UNA NOTICIA
    # =====================================================

    def get_age_days(article):

        try:

            published = article.get("published", "")

            if not published:
                return 999

            parsed = datetime.strptime(
                published[:25],
                "%a, %d %b %Y %H:%M:%S"
            )

            parsed = parsed.replace(tzinfo=timezone.utc)

            return max(
                0,
                (now - parsed).days
            )

        except Exception:

            return 999


    # =====================================================
    # PESO SEGÚN ANTIGÜEDAD DE LA NOTICIA
    # =====================================================

    def age_multiplier(days):

        if days <= 7:
            return 1.0

        elif days <= 30:
            return 0.75

        elif days <= 60:
            return 0.50

        elif days <= 120:
            return 0.25

        else:
            return 0.10


    # =====================================================
    # ANALIZAR NOTICIAS
    # =====================================================

    for article in articles:

        title = article["title"].lower()

        days_old = get_age_days(article)

        multiplier = age_multiplier(days_old)


        # ----------------------------------------------
        # BUSCAR RECUPERACIÓN
        # ----------------------------------------------

        recovery_match = any(
            keyword in title
            for keyword in RECOVERY_KEYWORDS
        )


        # ----------------------------------------------
        # BUSCAR RIESGO ALTO
        # ----------------------------------------------

        high_match = any(
            keyword in title
            for keyword in HIGH_RISK_KEYWORDS
        )


        # ----------------------------------------------
        # BUSCAR RIESGO MEDIO
        # ----------------------------------------------

        medium_match = any(
            keyword in title
            for keyword in MEDIUM_RISK_KEYWORDS
        )


        # ----------------------------------------------
        # CLASIFICAR
        # ----------------------------------------------

        if high_match:

            points = round(35 * multiplier)

            score += points

            article["risk"] = "high"

            article["points"] = points

            article["days_old"] = days_old

            high_alerts.append(article)


        elif medium_match:

            points = round(15 * multiplier)

            score += points

            article["risk"] = "medium"

            article["points"] = points

            article["days_old"] = days_old

            medium_alerts.append(article)


        elif recovery_match:

            # Las señales de recuperación restan riesgo
            points = round(20 * multiplier)

            score -= points

            article["risk"] = "recovery"

            article["points"] = -points

            article["days_old"] = days_old

            recovery_alerts.append(article)


        else:

            article["risk"] = "none"

            article["days_old"] = days_old


    # =====================================================
    # EVITAR SCORE NEGATIVO O SUPERIOR A 100
    # =====================================================

    score = max(0, min(score, 100))


    # =====================================================
    # CLASIFICACIÓN FINAL
    # =====================================================

    if score >= 70:

        status = "🔴 RIESGO ALTO"
        label = "alto"

    elif score >= 40:

        status = "🟠 RIESGO MEDIO-ALTO"
        label = "medio-alto"

    elif score >= 20:

        status = "🟡 RIESGO MODERADO"
        label = "moderado"

    else:

        status = "🟢 RIESGO BAJO"
        label = "bajo"


    return {
        "player": player_name,
        "score": score,
        "status": status,
        "label": label,
        "high_alerts": high_alerts,
        "medium_alerts": medium_alerts,
        "recovery_alerts": recovery_alerts,
        "articles": articles
    }
