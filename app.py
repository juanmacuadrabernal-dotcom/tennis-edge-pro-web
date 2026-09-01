import os
import streamlit as st
import pandas as pd
import numpy as np

from player_news import analyse_physical_status
from database import init_db, get_matches, get_last_update, get_model_metrics
from updater import update_database
from model import train_model, predict_match
from ratings import player_elo_table
from player_news import analyse_physical_status

st.set_page_config(page_title="Tennis Edge Pro", page_icon="🎾", layout="wide")
init_db()

@st.cache_data(ttl=600)
def load_data():
    return get_matches()

st.title("🎾 TENNIS EDGE PRO")
st.caption("Predicción estadística con forma reciente, superficie, Elo, ranking, servicio, devolución y modelo entrenado.")

with st.sidebar:
    st.header("⚙️ Centro de control")
    last = get_last_update() or "Sin actualizar"
    st.caption(f"Base de datos: {last}")

    if st.button("🔄 ACTUALIZAR DATOS", use_container_width=True):
        with st.spinner("Descargando y consolidando partidos..."):
            msg = update_database()
        load_data.clear()
        st.success(msg)

    if st.button("🧠 ENTRENAR MODELO", use_container_width=True):
        df = load_data()
        with st.spinner("Entrenando y validando el modelo..."):
            result = train_model(df)
        if result["ok"]:
            st.success(f"Modelo entrenado · Accuracy de validación: {result['accuracy']:.1%}")
        else:
            st.error(result["message"])

    superficie = st.selectbox("Superficie del partido", ["Hard", "Clay", "Grass", "Todas"])
    ventana = st.slider("Forma reciente: últimos partidos", 10, 60, 25)
    usar_elo = st.checkbox("Usar Elo por superficie", value=True)

df = load_data()
if df.empty:
    st.warning("La base de datos está vacía. Pulsa ACTUALIZAR DATOS.")
    st.stop()

players = sorted(set(df["winner_name"].dropna()) | set(df["loser_name"].dropna()))

# Búsqueda cómoda
c1, c2 = st.columns(2)
with c1:
    player_a = st.selectbox("👤 JUGADOR A", players)
with c2:
    player_b = st.selectbox("👤 JUGADOR B", players, index=min(1, len(players)-1))
st.markdown("## 💰 Cuotas de la casa de apuestas")

q1, q2 = st.columns(2)

with q1:
    cuota_a = st.number_input(
        f"Cuota de {player_a}",
        min_value=1.01,
        value=1.50,
        step=0.01,
        format="%.2f"
    )

with q2:
    cuota_b = st.number_input(
        f"Cuota de {player_b}",
        min_value=1.01,
        value=2.50,
        step=0.01,
        format="%.2f"
    )

metrics = get_model_metrics()
if metrics:
    st.info(f"🧠 Modelo guardado | Accuracy validación: **{float(metrics.get('accuracy', 0)):.1%}** | Entrenado: {metrics.get('trained_at','')}")

if st.button("🚀 ANALIZAR PARTIDO", type="primary", use_container_width=True):
    if player_a == player_b:
        st.error("Selecciona dos jugadores diferentes.")
        st.stop()

    result = predict_match(
        df, player_a, player_b,
        surface=None if superficie == "Todas" else superficie,
        recent_window=ventana,
        use_elo=usar_elo
    )

    if not result["ok"]:
        st.error(result["message"])
        st.stop()

    pa, pb = result["prob_a"], result["prob_b"]
    fav = player_a if pa >= pb else player_b

    st.markdown("## 🔮 Probabilidad estimada")
    x, y = st.columns(2)
    with x:
        st.metric(player_a, f"{pa*100:.1f}%")
        st.progress(int(pa*100))
    with y:
        st.metric(player_b, f"{pb*100:.1f}%")
        st.progress(int(pb*100))

    st.markdown("## 💰 Análisis de cuotas y valor esperado")

    # Probabilidad implícita de las cuotas
    implied_a = 1 / cuota_a
    implied_b = 1 / cuota_b

    # Valor esperado por cada unidad teórica
    ev_a = (pa * cuota_a) - 1
    ev_b = (pb * cuota_b) - 1

    # Diferencia entre modelo y mercado
    edge_a = pa - implied_a
    edge_b = pb - implied_b

    ca, cb = st.columns(2)

    with ca:
        st.subheader(player_a)

        st.write(f"💰 Cuota: **{cuota_a:.2f}**")

        st.write(
            f"📊 Probabilidad del modelo: "
            f"**{pa*100:.1f}%**"
        )

        st.write(
            f"🏦 Probabilidad implícita: "
            f"**{implied_a*100:.1f}%**"
        )

        st.write(
            f"⚡ Ventaja estimada: "
            f"**{edge_a*100:+.1f}%**"
        )

        st.write(
            f"💸 Valor esperado (EV): "
            f"**{ev_a*100:+.1f}%**"
        )

        if ev_a > 0.05:
            st.success("🟢 POSIBLE VALOR POSITIVO SEGÚN EL MODELO")

        elif ev_a > 0:
            st.warning("🟡 VALOR POSITIVO PEQUEÑO SEGÚN EL MODELO")

        else:
            st.error("🔴 SIN VALOR SEGÚN EL MODELO")


    with cb:
        st.subheader(player_b)

        st.write(f"💰 Cuota: **{cuota_b:.2f}**")

        st.write(
            f"📊 Probabilidad del modelo: "
            f"**{pb*100:.1f}%**"
        )

        st.write(
            f"🏦 Probabilidad implícita: "
            f"**{implied_b*100:.1f}%**"
        )

        st.write(
            f"⚡ Ventaja estimada: "
            f"**{edge_b*100:+.1f}%**"
        )

        st.write(
            f"💸 Valor esperado (EV): "
            f"**{ev_b*100:+.1f}%**"
        )

        if ev_b > 0.05:
            st.success("🟢 POSIBLE VALOR POSITIVO SEGÚN EL MODELO")

        elif ev_b > 0:
            st.warning("🟡 VALOR POSITIVO PEQUEÑO SEGÚN EL MODELO")

        else:
            st.error("🔴 SIN VALOR SEGÚN EL MODELO")
    st.success(f"🏆 FAVORITO ESTADÍSTICO: **{fav}**")
    st.caption("Confianza del modelo: " + result["confidence_label"])

    st.markdown("## 📊 Factores analizados")
    table = pd.DataFrame(result["comparison"])
    st.dataframe(table, hide_index=True, use_container_width=True)

    st.markdown("## 🥊 Enfrentamientos directos")
    h = result["h2h"]
    st.write(f"**{player_a}: {h['a_wins']}** — **{player_b}: {h['b_wins']}**  ·  Total: {h['total']}")

    if usar_elo:
        st.markdown("## ⚡ Elo")
        e1, e2 = st.columns(2)
        e1.metric(player_a, f"{result['elo_a']:.0f}")
        e2.metric(player_b, f"{result['elo_b']:.0f}")

    st.markdown("## 🎯 Cómo leer el resultado")
    st.write(result["explanation"])
    st.markdown("## 🩺 Estado físico y noticias recientes")

    with st.spinner("Buscando noticias recientes sobre los jugadores..."):

        physical_a = analyse_physical_status(player_a)
        physical_b = analyse_physical_status(player_b)


    col_a, col_b = st.columns(2)


    with col_a:

        st.subheader(player_a)

        st.write(
            f"Estado detectado: "
            f"**{physical_a['status']}**"
        )


        if physical_a["alerts"]:

            st.warning(
                "⚠️ Se han encontrado noticias "
                "potencialmente relacionadas con "
                "lesiones o problemas físicos."
            )


            for article in physical_a["alerts"]:

                st.write(
                    "🚨 " + article["title"]
                )

                if article["published"]:

                    st.caption(
                        article["published"]
                    )

                if article["link"]:

                    st.link_button(
                        "Leer noticia",
                        article["link"],
                        use_container_width=True
                    )

        else:

            st.success(
                "No se han detectado alertas "
                "físicas evidentes en las noticias encontradas."
            )


        with st.expander(
            "📰 Ver noticias encontradas"
        ):

            for article in physical_a["articles"]:

                st.write(
                    "• " + article["title"]
                )

                if article["link"]:

                    st.link_button(
                        "Abrir noticia",
                        article["link"]
                    )



    with col_b:

        st.subheader(player_b)

        st.write(
            f"Estado detectado: "
            f"**{physical_b['status']}**"
        )


        if physical_b["alerts"]:

            st.warning(
                "⚠️ Se han encontrado noticias "
                "potencialmente relacionadas con "
                "lesiones o problemas físicos."
            )


            for article in physical_b["alerts"]:

                st.write(
                    "🚨 " + article["title"]
                )

                if article["published"]:

                    st.caption(
                        article["published"]
                    )

                if article["link"]:

                    st.link_button(
                        "Leer noticia",
                        article["link"],
                        use_container_width=True
                    )

        else:

            st.success(
                "No se han detectado alertas "
                "físicas evidentes en las noticias encontradas."
            )


        with st.expander(
            "📰 Ver noticias encontradas"
        ):

            for article in physical_b["articles"]:

                st.write(
                    "• " + article["title"]
                )

                if article["link"]:

                    st.link_button(
                        "Abrir noticia",
                        article["link"]
                    )

st.divider()
st.caption("⚠️ Herramienta educativa y estadística. Las probabilidades son estimaciones, no garantías de resultado ni de beneficio económico.")
