"""Begin hier: 1. inlezen, 2. aanvullen, 3. filteren, 4. grafieken tonen."""
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from api import KENMERKEN, aanvullen, audio_voor_grafiek, ververs_genres, ververs_audio
from grafieken import METINGEN, selectie, samenvatting, dekking, audio_data
from grafieken import plot_genre, plot_taak, plot_audio, plot_verdeling

st.set_page_config(page_title="Muziek en studeren", layout="wide")
st.title("Muziek en studeren")
st.write("**Onderzoeksvraag:** welke muziek verkiezen studenten tijdens het studeren, "
         "en welke samenhang zien we met energie, stemming en studiemoeilijkheid?")

# 1. Lees de drie tabellen en de eerder opgehaalde API-resultaten in.
map_data = Path(__file__).resolve().parent
try:
    origineel = pd.read_csv(map_data / "dashboard_data.csv")
    voorkeuren = pd.read_csv(map_data / "studenten_voorkeuren.csv")
    spotify = pd.read_csv(map_data / "spotify_genres.csv")
    opgeslagen = json.loads((map_data / "api_resultaten.json").read_text(encoding="utf-8"))
except (OSError, ValueError) as fout:
    st.error("Een databestand ontbreekt of is onleesbaar. Upload alle bestanden uit de dashboardmap.")
    st.stop()
opgeslagen = st.session_state.get("api_resultaten", opgeslagen)

# 2. Vul alleen lege muziekvelden. De brondata blijven in 'origineel'.
df = aanvullen(origineel, opgeslagen)
broninfo = opgeslagen["broninfo"]
# Alleen bij het tellen: één rij per oorspronkelijk antwoord, herkenbaar aan _bronrij.
antwoorden = df.drop_duplicates("_bronrij")
voor = origineel.drop_duplicates("_bronrij")
st.caption(f"Voorkeuren van {broninfo['studenten']} studenten, {len(antwoorden)} antwoorden "
           "uit een aparte meting en Spotify-muziekgegevens. Dit zijn verschillende datasets; samenhang is geen oorzaak.")
tab1, tab2, tab3 = st.tabs(["1. Muziekvoorkeuren", "2. Muziek en ervaringen", "3. Data en bronnen"])

# 3. Vergelijk voorkeuren en muziekkenmerken in de twee losse datasets.
with tab1:
    st.subheader("Veranderen voorkeuren tijdens het studeren?")
    st.write("Dezelfde studenten beoordeelden genres voor dagelijks luisteren en voor studeren.")
    vergelijking = voorkeuren.pivot(index="Genre", columns="Context", values="Gemiddelde")
    vergelijking["Verschil"] = vergelijking["Tijdens studeren"] - vergelijking["Dagelijks"]
    vergelijking["Aantal"] = voorkeuren.groupby("Genre")["Aantal"].min()
    vergelijking = vergelijking.sort_values("Verschil")
    grootste = vergelijking["Verschil"].abs().idxmax()
    verschil = vergelijking.loc[grootste, "Verschil"]
    if st.checkbox("Toon het verschil in plaats van de twee gemiddelden", value=True):
        fig = px.bar(vergelijking.reset_index(), x="Verschil", y="Genre", orientation="h",
                     text=vergelijking["Verschil"].map(lambda x: f"{x:+.2f}"), hover_data=["Aantal"],
                     labels={"Verschil": "Studievoorkeur minus dagelijkse voorkeur"})
        fig.add_vline(x=0, line_color="gray", line_dash="dash")
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.add_annotation(x=verschil, y=grootste, text="Grootste verschil", showarrow=True, ax=100, ay=-30)
    else:
        fig = px.bar(voorkeuren, x="Gemiddelde", y="Genre", color="Context", pattern_shape="Context",
                     orientation="h", barmode="group", hover_data=["Aantal"],
                     category_orders={"Genre": vergelijking.index.tolist()},
                     labels={"Gemiddelde": "Gemiddelde voorkeursscore"},
                     color_discrete_map={"Dagelijks": "#0072B2", "Tijdens studeren": "#D55E00"},
                     pattern_shape_map={"Dagelijks": "", "Tijdens studeren": "/"})
        fig.update_layout(legend=dict(orientation="h", y=1.07))
    fig.update_layout(height=850, margin=dict(l=10, r=80, t=60, b=40))
    st.plotly_chart(fig, use_container_width=True, key="voorkeuren")
    st.write(f"**Wat zien we?** Het grootste verschil is bij {grootste}: {verschil:+.2f} punten. "
             "Dit beschrijft voorkeur, geen effect op concentratie. De groepen zijn dezelfde studenten.")

    st.subheader("Welke muziekkenmerken hebben Spotify-genres?")
    st.write("De genre-indeling verschilt van de vragenlijst; we koppelen deze gemiddelden niet aan studenten.")
    kenmerk = st.selectbox("Vergelijk muziekkenmerk", KENMERKEN)
    st.caption("energy = geluidsintensiteit; valence = positieve klank; tempo = beats per minuut; "
               "danceability = dansbaarheid. Dit beschrijft de muziek, niet hoe een student zich voelt.")
    aantal = st.slider("Aantal genres met het hoogste gemiddelde", 5, int(broninfo["spotify_genres"]), 15)
    sub = spotify[spotify["Kenmerk"] == kenmerk].nlargest(aantal, "Gemiddelde").sort_values("Gemiddelde")
    fig = px.bar(sub, x="Gemiddelde", y="Genre", orientation="h", hover_data=["Aantal"],
                 labels={"Gemiddelde": f"Gemiddelde {kenmerk}", "Aantal": "Geldige Spotify-rijen"})
    fig.update_layout(height=max(450, 25 * aantal + 100))
    st.plotly_chart(fig, use_container_width=True, key="spotify")
    st.caption(f"{broninfo['spotify_gebruikt']:,} Spotify-rijen, inclusief dubbele bronrijen. "
               "Je ziet de gekozen hoogste gemiddelden, niet alle genres.")

# 4. De dropdowns filteren alle grafieken in dit tabblad.
with tab2:
    st.subheader("Hangen muziek en ervaringen samen?")
    st.write("Energieverschil en stemmingsverschil = later min begin. "
             "Bij een ontbrekende begin- of eindmeting blijft het verschil leeg.")
    meting = st.selectbox("Kies uitkomst", METINGEN)
    beschikbaar = antwoorden.loc[antwoorden[meting].notna(), "Aan het studeren"].unique()
    contexten = {"Alle antwoorden": None}
    for code, label in [("Yes", "Tijdens studeren"), ("No", "Niet tijdens studeren")]:
        if code in beschikbaar:
            contexten[label] = code
    context = st.selectbox("Studiecontext bij deze uitkomst", list(contexten))
    gekozen = df if contexten[context] is None else df[df["Aan het studeren"] == contexten[context]]
    genre_data = gekozen.copy()
    if st.checkbox("Gebruik ook aangevulde genres uit iTunes", value=True):
        genre_data["track_genre"] = gekozen["track_genre"] + " [" + gekozen["Genrebron"] + "]"
    else:
        genre_data["track_genre"] = origineel.loc[gekozen.index, "track_genre"]
    minimum = st.slider("Minimumaantal geldige antwoorden per genre", 1, 20, 1)
    toon_tabel = st.checkbox("Toon de tabel bij de genrevergelijking", value=True)
    st.caption(dekking(gekozen, selectie(genre_data, "track_genre", meting, minimum)))
    st.plotly_chart(plot_genre(genre_data, meting, minimum), use_container_width=True, key="genre")
    if toon_tabel:
        st.dataframe(samenvatting(genre_data, "track_genre", meting, minimum), hide_index=True)
    st.write("Elk punt is één antwoord per genre. De bron staat erbij omdat Spotify en iTunes genres anders indelen. "
             "Weinig antwoorden en herhaalde deelnemers maken de vergelijking onzeker.")

    st.subheader("Andere verklaring: de studiecontext")
    st.write("Misschien hangt de uitkomst ook samen met wel of niet studeren. Deze tabel vergelijkt beide contexten vóór het filter.")
    context_tabel = (antwoorden.groupby("Aan het studeren")[meting].agg(Antwoorden="count", Gemiddelde="mean")
                     .query("Antwoorden > 0").rename(index={"Yes": "Tijdens studeren", "No": "Niet tijdens studeren"}))
    st.dataframe(context_tabel.round(2))
    if len(context_tabel) == 2:
        verschil_context = context_tabel.loc["Tijdens studeren", "Gemiddelde"] - context_tabel.loc["Niet tijdens studeren", "Gemiddelde"]
        st.write(f"Tijdens min niet tijdens studeren: {verschil_context:+.2f} punten. "
                 "De groepen zijn niet willekeurig samengesteld; dit bewijst geen oorzakelijk effect.")
    else:
        st.info("Slechts één context heeft geldige antwoorden; vergelijken is niet mogelijk.")

    st.subheader("Vergelijk ook de studietaken")
    st.caption(dekking(gekozen, selectie(gekozen, "Studietaak", meting)))
    st.write("De balken tonen gemiddelden met standaarddeviatie; de boxplot toont de spreiding. Het genre-minimumfilter geldt hier niet.")
    st.plotly_chart(plot_taak(gekozen, meting), use_container_width=True, key="taak_gemiddelde")
    st.plotly_chart(plot_taak(gekozen, meting, box=True), use_container_width=True, key="taak_spreiding")

    st.subheader("Audiokenmerken en de gekozen uitkomst")
    audiobron = st.selectbox("Bron van de audiokenmerken", ["ReccoBeats API", "Oorspronkelijke Spotify-dataset"])
    audio_selectie = origineel.loc[gekozen.index]
    if audiobron == "ReccoBeats API":
        audio_selectie = audio_voor_grafiek(gekozen, opgeslagen["reccobeats"])
    st.caption(dekking(audio_selectie, audio_data(audio_selectie, meting)))
    st.plotly_chart(plot_audio(audio_selectie, meting), use_container_width=True, key="audio")
    st.caption("Eén antwoord per punt; meerdere tracks worden gemiddeld. De trendlijn is verkennend. "
               "We kiezen één bron per grafiek omdat hun meetmethoden kunnen verschillen.")
    st.subheader("Verdeling van de antwoorden")
    st.caption(dekking(gekozen, selectie(gekozen, None, meting)))
    st.plotly_chart(plot_verdeling(gekozen, meting), use_container_width=True, key="verdeling")

# 5. Laat zien wat is aangevuld, welke waarden ontbreken en waar de data vandaan komen.
with tab3:
    st.subheader("Wat is aangevuld en gecontroleerd?")
    velden = ["track_genre", *KENMERKEN]
    st.dataframe(pd.DataFrame({"Ontbrekend vóór": voor[velden].isna().sum(),
                               "Ontbrekend na": antwoorden[velden].isna().sum()}))
    st.caption("Dit telt oorspronkelijke antwoorden. iTunes koppelt op titel + artiest; ReccoBeats op exact Spotify-track-ID.")
    st.write("De gevonden waarden staan direct in de df, met twee bronkolommen. Alleen lege muziekvelden zijn ingevuld. "
             "Studentmetingen en popularity zijn niet geschat. Alle oorspronkelijke rijen blijven behouden.")
    st.write(f"**Oorspronkelijke merge:** {len(voor)} antwoorden werden {len(df)} mergerijen. "
             f"{voor['track_id'].notna().sum()} antwoorden hadden een Spotify-datasetmatch: eerst op ID, daarna titel + artiest. "
             "Meerdere matches veroorzaken extra rijen. Grafieken tellen elk antwoord eenmaal, of eenmaal per genre.")
    st.write(f"**Spotify-bron:** {broninfo['spotify_bronrijen']:,} rijen, waarvan {broninfo['spotify_gebruikt']:,} gebruikt. "
             "Eén rij zonder bruikbare speelduur is uitgesloten. Dubbele rijen en nulwaarden bij tempo zijn behouden.")
    st.write("**Variabelen:** voorkeuren, genre, audiokenmerken en uitkomsten dragen het verhaal. "
             "Studiecontext en studietaak helpen andere verklaringen te bekijken.")
    eindtabel = df.drop(columns="_bronrij")  # Technische sleutel alleen nodig om grafiekpunten eerlijk te tellen.
    numeriek = eindtabel.select_dtypes(include="number")
    kwaliteit = pd.DataFrame({"Ontbrekend": eindtabel.isna().sum(), "Ontbrekend (%)": eindtabel.isna().mean().mul(100).round(1),
                              "Minimum": numeriek.min(), "Maximum": numeriek.max()})
    st.dataframe(kwaliteit)
    st.caption(f"Deze tabel telt alle {len(df)} mergerijen; {eindtabel.duplicated().sum()} volledig identieke extra rijen zijn behouden.")
    buiten = ((df[["energy", "valence", "danceability"]] < 0) | (df[["energy", "valence", "danceability"]] > 1)).sum().sum()
    st.write(f"Bereikcheck: {buiten} waarden buiten 0–1; {(df['tempo'] < 0).sum()} negatieve tempo's.")
    with st.expander("Bekijk en download de eind-df"):
        st.dataframe(eindtabel, hide_index=True)
        st.download_button("Download eind-df", eindtabel.to_csv(index=False).encode("utf-8-sig"), "dashboard_aangevuld.csv", "text/csv")

    with st.expander("API-gegevens opnieuw ophalen en bewaren"):
        st.write("Opgeslagen resultaten laden direct. Opnieuw ophalen bij iTunes duurt ongeveer acht minuten. "
                 "Alleen titels/artiesten gaan naar Apple; alleen track-ID's naar ReccoBeats. Geen tokens nodig.")
        bron = st.selectbox("Welke bron verversen?", ["itunes", "reccobeats"])
        if st.button("Haal gegevens opnieuw op"):
            balk = st.progress(0)
            def voortgang(i, totaal):
                balk.progress(i / totaal, text=f"{i} van {totaal} opgezocht")
            ophalen = ververs_genres if bron == "itunes" else ververs_audio
            opgeslagen[bron] = ophalen(origineel, opgeslagen[bron], voortgang)
            st.session_state["api_resultaten"] = opgeslagen
            st.rerun()
        fouten = sum(r.get("status", "").startswith("API") for r in opgeslagen[bron].values())
        if fouten:
            st.info(f"Bij {fouten} zoekopdrachten was de API niet bereikbaar. Opgeslagen gegevens blijven bruikbaar.")
        st.dataframe(pd.DataFrame.from_dict(opgeslagen[bron], orient="index"))
        st.download_button("Download API-resultaten", json.dumps(opgeslagen, ensure_ascii=False, indent=2), "api_resultaten.json", "application/json")
        st.caption("Vervang api_resultaten.json in GitHub om vernieuwde resultaten blijvend te bewaren.")
    with st.expander("Bronnen en uitleg"):
        st.markdown((map_data / "README.md").read_text(encoding="utf-8"))

st.divider()
st.subheader("Conclusie")
lager = (vergelijking["Verschil"] < 0).sum()
st.write(f"Bij {lager} van de {len(vergelijking)} genres is de studievoorkeur lager dan de dagelijkse voorkeur. "
         f"Het grootste verschil is {grootste} ({verschil:+.2f} punten). De gekoppelde ervaringen bevatten veel minder "
         "geldige antwoorden en bewijzen niet dat een genre energie, stemming of studieprestaties verbetert.")
