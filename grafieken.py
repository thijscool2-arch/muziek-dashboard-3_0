"""Grafieken op aparte kopieën; de oorspronkelijke df blijft intact.

Bronnen: https://plotly.com/python/strip-charts/
         https://plotly.com/python/error-bars/
Code opgesteld met hulp van Codex en aangepast aan deze datasets.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = ["#0072B2", "#D55E00"]

METINGEN = ["Energieverschil", "Stemmingsverschil", "Moeilijkheid studie"]
KENMERKEN = ["energy", "valence", "tempo", "danceability"]


def selectie(data, groep, meting, minimum=1):
    # Alleen in de grafiektabel: elk antwoord eenmaal per genre of studietaak.
    sleutels = ["_bronrij"] + ([groep] if groep else [])
    nodig = [meting] + ([groep] if groep else [])
    sub = data.dropna(subset=nodig).drop_duplicates(subset=sleutels).copy()
    if groep:
        aantallen = sub.groupby(groep)[meting].transform("count")
        sub = sub[aantallen >= minimum].copy()
    return sub


def dekking(data, sub):
    totaal = data["_bronrij"].nunique()
    geldig = sub["_bronrij"].nunique()
    deelnemers = sub["Deelnemer ID"].nunique()
    return (f"{geldig} van {totaal} oorspronkelijke antwoorden getoond, van {deelnemers} deelnemers. "
            f"{totaal - geldig} antwoorden niet getoond door ontbrekende waarden of het gekozen filter.")


def samenvatting(data, groep, meting, minimum=1):
    sub = selectie(data, groep, meting, minimum)
    return (sub.groupby(groep)[meting].agg(Antwoorden="count", Gemiddelde="mean", Spreiding="std")
            .reset_index().sort_values("Gemiddelde").round(2))


def afmaken(fig, titel, aantal=8):
    fig.update_layout(title=titel, height=max(420, 35 * aantal + 150), showlegend=False)
    fig.add_vline(x=0, line_dash="dash", line_color="gray")
    return fig


def leeg(titel):
    fig = go.Figure()
    fig.add_annotation(text="Geen geldige antwoorden voor deze selectie.", showarrow=False)
    fig.update_layout(title=titel, height=350)
    return fig


def plot_genre(data, meting, minimum=1):
    sub = selectie(data, "track_genre", meting, minimum)
    titel = f"{meting} per genre — elk punt is een antwoord"
    if sub.empty:
        return leeg(titel)
    aantallen = sub["track_genre"].value_counts()
    sub["Genre (n)"] = sub["track_genre"].map(lambda g: f"{g} (n={aantallen[g]})")
    volgorde = sub.groupby("Genre (n)")[meting].median().sort_values().index.tolist()
    fig = px.strip(sub, x=meting, y="Genre (n)", category_orders={"Genre (n)": volgorde})
    fig.update_traces(marker=dict(size=9, opacity=0.7))
    return afmaken(fig, titel, len(volgorde))


def plot_taak(data, meting, box=False):
    sub = selectie(data, "Studietaak", meting)
    titel = f"{meting} per studietaak"
    if sub.empty:
        return leeg(titel)
    if box:
        aantallen = sub["Studietaak"].value_counts()
        sub["Taak (n)"] = sub["Studietaak"].map(lambda t: f"{t} (n={aantallen[t]})")
        fig = px.box(sub, x=meting, y="Taak (n)", points="all")
    else:
        tabel = samenvatting(data, "Studietaak", meting)
        fig = px.bar(tabel, x="Gemiddelde", y="Studietaak", orientation="h",
                     error_x="Spreiding", text=tabel["Antwoorden"].map(lambda n: f"n={n}"))
        fig.update_traces(textposition="outside")
        titel += "<br><sup>Foutbalk = standaarddeviatie (spreiding); bij n=1 niet berekenbaar.</sup>"
    return afmaken(fig, titel, sub["Studietaak"].nunique())


def audio_data(data, meting):
    # Eén punt per antwoord per kenmerk. Meerdere gekoppelde tracks: gemiddelde
    # over verschillende tracks, zodat genreduplicaten geen extra gewicht geven.
    tracks = data.dropna(subset=["track_id"]).drop_duplicates(["_bronrij", "track_id"])
    audio = tracks.groupby("_bronrij")[KENMERKEN].mean().reset_index()
    antwoorden = data.drop_duplicates("_bronrij")[["_bronrij", "Deelnemer ID", meting]]
    lang = antwoorden.merge(audio, on="_bronrij").melt(
        id_vars=["_bronrij", "Deelnemer ID", meting], value_vars=KENMERKEN,
        var_name="Kenmerk", value_name="Waarde")
    # Ontbrekende waarden per kenmerk behandelen, niet alle kenmerken tegelijk eisen.
    return lang.dropna(subset=[meting, "Waarde"]).copy()


def plot_audio(data, meting):
    sub = audio_data(data, meting)
    titel = f"Audiokenmerken en {meting.lower()} — met verkennende trendlijn"
    if sub.empty:
        return leeg(titel)
    aantallen = sub["Kenmerk"].value_counts()
    sub["Kenmerk (n)"] = sub["Kenmerk"].map(lambda k: f"{k} (n={aantallen[k]})")
    trend = "ols" if sub[meting].nunique() > 1 else None
    if trend is None:
        titel = f"Audiokenmerken en {meting.lower()} — geen trendlijn bij een constante uitkomst"
    fig = px.scatter(sub, x="Waarde", y=meting, facet_col="Kenmerk (n)", facet_col_wrap=2,
                     trendline=trend, trendline_color_override="#D55E00")
    fig.update_xaxes(matches=None)
    fig.update_traces(marker=dict(size=9, opacity=0.7))
    fig.update_layout(title=titel, height=550)
    return fig


def plot_verdeling(data, meting):
    sub = selectie(data, None, meting)
    titel = f"Verdeling van {meting.lower()} — {len(sub)} antwoorden"
    if sub.empty:
        return leeg(titel)
    aantallen = sub[meting].value_counts().sort_index().rename_axis(meting).reset_index(name="Antwoorden")
    return px.bar(aantallen, x=meting, y="Antwoorden", title=titel)
