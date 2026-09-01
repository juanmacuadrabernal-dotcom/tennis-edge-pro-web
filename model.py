from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss
from database import set_model_metrics
from ratings import elo_ratings

MODEL_PATH = Path("tennis_model.joblib")
FEATURES = ["rank_diff","form_diff","surface_form_diff","elo_diff"]

def _player_history(df, player, before_date, surface=None, n=25):
    x = df[df["tourney_date"] < before_date]
    if surface:
        sx = x[x["surface"].fillna("") == surface]
        if len(sx) >= 5:
            x = sx
    x = x[(x.winner_name == player) | (x.loser_name == player)].sort_values("tourney_date", ascending=False).head(n)
    if x.empty:
        return None
    wins = (x.winner_name == player).sum()
    ranks = pd.concat([
        x.loc[x.winner_name == player, "winner_rank"],
        x.loc[x.loser_name == player, "loser_rank"]
    ])
    ranks = pd.to_numeric(ranks, errors="coerce").dropna()
    return {"form": wins/len(x), "rank": ranks.mean() if len(ranks) else 999.0}

def train_model(df):
    if len(df) < 100:
        return {"ok": False, "message": "No hay suficientes partidos."}

    x = df.dropna(subset=["tourney_date","winner_name","loser_name"]).sort_values("tourney_date").copy()
    # Entrenamiento con orientación aleatoria para evitar que el modelo aprenda
    # que la columna winner siempre significa victoria.
    rows = []
    elos = {}
    base, k = 1500.0, 28.0

    for _, r in x.iterrows():
        date = r.tourney_date
        surface = r.surface if pd.notna(r.surface) else None
        a, b = r.winner_name, r.loser_name

        ha = _player_history(x, a, date, surface, 25)
        hb = _player_history(x, b, date, surface, 25)
        if ha and hb:
            ea, eb = elos.get(a, base), elos.get(b, base)
            rank_diff = hb["rank"] - ha["rank"]
            row = [rank_diff, ha["form"]-hb["form"], ha["form"]-hb["form"], ea-eb]
            rows.append((row, 1))

            # Simetría: mismo partido al revés, etiqueta 0.
            rows.append(([-row[0], -row[1], -row[2], -row[3]], 0))

        ea, eb = elos.get(a, base), elos.get(b, base)
        exp = 1/(1+10**((eb-ea)/400))
        elos[a] = ea + k*(1-exp)
        elos[b] = eb + k*(0-exp)

    if len(rows) < 200:
        return {"ok": False, "message": "No hay suficiente historial útil para entrenar."}

    data = pd.DataFrame([r[0] for r in rows], columns=FEATURES)
    y = np.array([r[1] for r in rows])

    # Validación temporal: últimos 20%.
    cut = int(len(data)*0.8)
    Xtr, Xte = data.iloc[:cut], data.iloc[cut:]
    ytr, yte = y[:cut], y[cut:]

    clf = HistGradientBoostingClassifier(max_iter=180, learning_rate=0.05, max_leaf_nodes=12, random_state=42)
    clf.fit(Xtr, ytr)
    p = clf.predict_proba(Xte)[:,1]
    acc = accuracy_score(yte, p >= .5)
    ll = log_loss(yte, p)
    brier = brier_score_loss(yte, p)

    joblib.dump(clf, MODEL_PATH)
    set_model_metrics({
        "accuracy": float(acc),
        "log_loss": float(ll),
        "brier": float(brier),
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "samples": len(data)
    })
    return {"ok": True, "accuracy": acc}

def _stats(df, player, surface, n):
    x = df.copy()
    total = x[(x.winner_name == player) | (x.loser_name == player)].sort_values("tourney_date", ascending=False).head(n)
    sx = x[x.surface.fillna("") == surface] if surface else total
    sx = sx[(sx.winner_name == player) | (sx.loser_name == player)].sort_values("tourney_date", ascending=False).head(n)
    use = sx if len(sx) >= 5 else total
    if use.empty: return None

    wins = int((use.winner_name == player).sum())
    ranks = pd.concat([
        use.loc[use.winner_name == player, "winner_rank"],
        use.loc[use.loser_name == player, "loser_rank"]
    ])
    ranks = pd.to_numeric(ranks, errors="coerce").dropna()

    def mean_stat(col):
        vals = pd.concat([
            use.loc[use.winner_name == player, "w_"+col],
            use.loc[use.loser_name == player, "l_"+col]
        ])
        return pd.to_numeric(vals, errors="coerce").mean()

    return {
        "matches": len(use), "wins": wins, "form": wins/len(use),
        "rank": ranks.mean() if len(ranks) else 999.0,
        "aces": mean_stat("ace"), "df": mean_stat("df"),
        "first": mean_stat("1stWon"), "second": mean_stat("2ndWon"),
        "break": mean_stat("bpWon")
    }

def _h2h(df,a,b,surface=None):
    x = df[((df.winner_name==a)&(df.loser_name==b))|((df.winner_name==b)&(df.loser_name==a))]
    if surface:
        sx=x[x.surface.fillna("")==surface]
        if not sx.empty: x=sx
    aw=int((x.winner_name==a).sum()) if not x.empty else 0
    bw=int((x.winner_name==b).sum()) if not x.empty else 0
    return aw,bw

def predict_match(df, a, b, surface=None, recent_window=25, use_elo=True):
    sa, sb = _stats(df,a,surface,recent_window), _stats(df,b,surface,recent_window)
    if not sa or not sb:
        return {"ok":False,"message":"No hay historial suficiente para ambos jugadores."}

    ratings = elo_ratings(df, surface if use_elo else None)
    ea, eb = ratings.get(a,1500.0), ratings.get(b,1500.0)

    # Si existe modelo entrenado se utiliza; si no, fórmula robusta.
    rank_diff = sb["rank"] - sa["rank"]
    form_diff = sa["form"] - sb["form"]
    features = pd.DataFrame([[rank_diff, form_diff, form_diff, ea-eb]], columns=FEATURES)

    if MODEL_PATH.exists():
        clf = joblib.load(MODEL_PATH)
        pa = float(clf.predict_proba(features)[0,1])
    else:
        z = 0.012*rank_diff + 2.2*form_diff + 0.002*(ea-eb)
        pa = float(1/(1+np.exp(-z)))

    ha,hb=_h2h(df,a,b,surface)
    if ha+hb >= 2:
        h=ha/(ha+hb)
        pa = 0.92*pa + 0.08*h

    pb=1-pa
    diff=abs(pa-pb)
    confidence="Alta" if diff>.25 else "Media" if diff>.10 else "Baja"

    comparison=[
        {"Factor":"Forma reciente","Jugador A":f"{sa['form']:.1%}","Jugador B":f"{sb['form']:.1%}"},
        {"Factor":"Partidos analizados","Jugador A":sa["matches"],"Jugador B":sb["matches"]},
        {"Factor":"Ranking medio reciente","Jugador A":f"{sa['rank']:.0f}","Jugador B":f"{sb['rank']:.0f}"},
        {"Factor":"Aces / partido","Jugador A":f"{sa['aces']:.2f}","Jugador B":f"{sb['aces']:.2f}"},
        {"Factor":"Dobles faltas / partido","Jugador A":f"{sa['df']:.2f}","Jugador B":f"{sb['df']:.2f}"},
        {"Factor":"Puntos ganados 1er saque","Jugador A":f"{sa['first']:.2f}","Jugador B":f"{sb['first']:.2f}"},
        {"Factor":"Puntos ganados 2º saque","Jugador A":f"{sa['second']:.2f}","Jugador B":f"{sb['second']:.2f}"},
    ]
    explanation = (
        f"El modelo da ventaja a {'Jugador A' if pa>=.5 else 'Jugador B'} "
        f"por la combinación de ranking, forma reciente, rendimiento disponible y Elo. "
        f"La diferencia de probabilidades es de {diff*100:.1f} puntos porcentuales."
    )

    return {"ok":True,"prob_a":pa,"prob_b":pb,"confidence_label":confidence,
            "comparison":comparison,"h2h":{"a_wins":ha,"b_wins":hb,"total":ha+hb},
            "elo_a":ea,"elo_b":eb,"explanation":explanation}
