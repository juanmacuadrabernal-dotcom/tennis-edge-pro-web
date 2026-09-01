from datetime import datetime
from io import StringIO
import hashlib

import pandas as pd
import requests

from database import (
    init_db,
    existing_keys,
    insert_matches,
    set_last_update
)


# FUENTES DE DATOS
# 1. Partidos ATP principales
# 2. Challenger y clasificación

SOURCES = [

    "https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main/atp/atp_matches_{}.csv",

    "https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main/atp/atp_matches_qual_chall_{}.csv"

]


def descargar_archivo(url):

    try:

        respuesta = requests.get(
            url,
            timeout=60
        )

        if respuesta.status_code != 200:
            return None

        if len(respuesta.text) < 1000:
            return None

        datos = pd.read_csv(
            StringIO(respuesta.text)
        )

        return datos

    except Exception:

        return None


def update_database(start_year=2020):

    init_db()

    frames = []

    current_year = datetime.now().year


    # DESCARGAR TODOS LOS AÑOS

    for year in range(
        start_year,
        current_year + 1
    ):

        print(
            f"Buscando partidos del año {year}..."
        )

        for source in SOURCES:

            url = source.format(year)

            df = descargar_archivo(url)

            if df is not None:

                if not df.empty:

                    frames.append(df)


    # COMPROBAR SI HEMOS DESCARGADO DATOS

    if not frames:

        return (
            "No se pudieron descargar datos. "
            "Revisa la conexión."
        )


    # UNIR TODOS LOS PARTIDOS

    df = pd.concat(
        frames,
        ignore_index=True,
        sort=False
    )


    # ELIMINAR FILAS SIN JUGADORES

    df = df.dropna(
        subset=[
            "winner_name",
            "loser_name"
        ]
    )


    # ALGUNAS FUENTES PUEDEN TENER COLUMNAS DIFERENTES

    if "tourney_date" not in df.columns:

        df["tourney_date"] = ""


    if "tourney_name" not in df.columns:

        df["tourney_name"] = ""


    # CREAR IDENTIFICADOR ÚNICO PARA CADA PARTIDO

    stable = (

        df["tourney_date"]
        .astype(str)

        + "|"

        + df["tourney_name"]
        .astype(str)

        + "|"

        + df["winner_name"]
        .astype(str)

        + "|"

        + df["loser_name"]
        .astype(str)

    )


    df["match_key"] = stable.map(

        lambda x:

        hashlib.sha1(
            x.encode("utf-8")
        ).hexdigest()

    )


    # BUSCAR PARTIDOS QUE YA EXISTEN

    existing = existing_keys()


    # QUEDARNOS SOLO CON LOS NUEVOS

    new = df.loc[
        ~df["match_key"].isin(existing)
    ].copy()


    # GUARDAR LOS PARTIDOS NUEVOS

    if not new.empty:

        insert_matches(new)


    # GUARDAR FECHA DE ACTUALIZACIÓN

    set_last_update()


    return (

        "Actualización completada. "

        f"Partidos nuevos añadidos: {len(new)}. "

        "Se han buscado datos ATP y Challenger."

    )