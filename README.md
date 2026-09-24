# Muziek en studeren

## Waar staat de code?

Begin bij **app.py**. Lees de genummerde Nederlandse opmerkingen van boven naar beneden.

| Bestand | Wat doet het? |
| --- | --- |
| app.py | Leest data in, maakt df, toont filters en bouwt het dashboard. |
| grafieken.py | Maakt de grafiektabellen en de grafieken. |
| api.py | Haalt muziekgegevens op en vult lege muziekvelden aan. |
| dashboard_data.csv | De oorspronkelijke merge, met `_bronrij` om antwoorden te herkennen. |
| spotify_genres.csv | Gemiddelde muziekkenmerken per Spotify-genre. |
| studenten_voorkeuren.csv | Gemiddelde genrevoorkeuren van 98 studenten. |
| api_resultaten.json | Eerder opgehaalde API-antwoorden en aantallen van de bronnen. |
| requirements.txt | Pakketten en geteste versies voor Python 3.13. |
| README.md | Deze uitleg en bronvermelding. |
| .gitignore | Houdt tijdelijke bestanden uit GitHub. |

## De eind-df en ontbrekende waarden

`df` in app.py bevat de aangevulde gegevens direct in de bestaande kolommen.
In tabblad 3 kun je die tabel bekijken en downloaden als dashboard_aangevuld.csv.
Genrebron en Aanvulling audiobron laten zien waar aanvullingen vandaan komen.
Ontbrekende studentmetingen en popularity blijven ongewijzigd.

Alle 323 mergerijen uit 280 oorspronkelijke antwoorden blijven behouden.
`_bronrij` is de sleutel van het oorspronkelijke antwoord. Die stond eerder
in een apart bestand en staat nu in dashboard_data.csv. Alleen voor grafieken
tellen we elk antwoord eenmaal, of eenmaal per genre. Dezelfde student kan
meerdere antwoorden geven; het aantal antwoorden is dus niet het aantal studenten.

Energie- en stemmingsverschil zijn de latere score min de beginscore.
Ontbreekt een van beide, dan blijft het verschil leeg. Bij een lege selectie
toont de grafiek een melding. Kleine aantallen en herhaalde deelnemers beperken conclusies.

Spotify en iTunes hebben verschillende genre-indelingen; de grafiek vermeldt
de bron en voegt die categorieën niet samen. Ook de audiobronnen zijn niet
als identiek gevalideerd: kies daarom één audiobron per grafiek. De OLS-trendlijn
is een verkennende lineaire fit. Foutbalken bij taken zijn standaarddeviaties,
geen betrouwbaarheidsintervallen. De contextvergelijking is beschrijvend, niet causaal.

De voorkeuren vergelijken twee beoordelingen door dezelfde 98 studenten.
Het gemarkeerde grootste verschil is geen significantietoets. De losse
Spotify-ranglijst gebruikt 113.999 van 114.000 bronrijen: één rij zonder
bruikbare speelduur is uitgesloten, duplicaten en nulwaarden bij tempo zijn behouden.

## API-werkwijze en bronnen

Code opgesteld met hulp van Codex en aangepast aan deze data.

- [iTunes Search API](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/Searching.html): zoekt titel en artiest met `entity=song`, `country=NL`, `limit=50`. Titel en artiest moeten overeenkomen na normalisatie van hoofdletters, accenten, leestekens en herstelbare tekencodering. Versiewoorden zoals live/remix blijven staan. Bij verschillende genres of geen match vullen we niets in. Minstens 3,2 seconden pauze per verzoek. Alleen titels en artiesten worden verstuurd.
- [ReccoBeats audiokenmerken](https://reccobeats.com/docs/apis/get-audio-features): GET `/v1/audio-features?ids=...`, per twintig Spotify-track-ID's. De teruggestuurde `href` koppelt de juiste ID aan energy, valence, tempo en danceability. Waarden buiten 0–1 of negatieve tempo's worden geweigerd. Eén seconde pauze tussen batches; alleen track-ID's worden verstuurd.
- [ReccoBeats authenticatie](https://reccobeats.com/docs/documentation/introduction) en [limieten](https://reccobeats.com/docs/documentation/rate-limiting). Er zijn geen tokens nodig. Tijdelijke fouten krijgen maximaal twee retries; numerieke Retry-After-headers worden gerespecteerd. Bij een storing blijven eerder opgeslagen resultaten behouden.
- [Plotly individuele punten](https://plotly.com/python/strip-charts/), [foutbalken](https://plotly.com/python/error-bars/), [trendlijnen](https://plotly.com/python/linear-fits/) en [patronen](https://plotly.com/python/pattern-hatching-texture/).
- [Streamlit widgets](https://docs.streamlit.io/develop/api-reference/widgets) en [tabbladen](https://docs.streamlit.io/develop/api-reference/layout/st.tabs).

API-resultaten bevatten status, opvraagmoment en bron-URL. De zoeklimiet van
vijftig betekent dat 'niet gevonden' niet bewijst dat een nummer niet bestaat.
Op 24 september 2026 werden via iTunes genres bij 76 extra antwoorden gevonden
(201 ontbrekend wordt 125); via ReccoBeats vier audiokenmerken bij 93 antwoorden
(elk van 201 naar 108 ontbrekend). De brondata blijven bewaard.

De oorspronkelijke datasets komen uit dataset 1 case 2.zip (Spotify),
dataset 2 case 2.xlsx (voorkeuren) en dataset 3 case 2.xlsx (ervaringen).
index.xlsx bevat de genrenamen van de vragenlijst. Voeg voor de inlevering
hun oorspronkelijke publicatielinks/auteurs toe; die zijn nog niet vastgesteld.
