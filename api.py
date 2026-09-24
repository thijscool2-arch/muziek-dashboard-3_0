"""Muziekgegevens ophalen en alleen lege waarden in de df aanvullen.

Bronnen, koppelsleutels en uitleg staan in README.md. Geen tokens nodig.
"""
import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

KENMERKEN = ["energy", "valence", "tempo", "danceability"]


def ophalen(url):
    """Probeer een API-verzoek maximaal drie keer; None betekent storing."""
    for poging in range(3):
        try:
            verzoek = Request(url, headers={"User-Agent": "MuziekDashboard/1.0"})
            with urlopen(verzoek, timeout=20) as antwoord:
                return json.load(antwoord)
        except (HTTPError, URLError, TimeoutError, ValueError) as fout:
            if poging == 2:
                return None
            wachten = 5 * (poging + 1)
            if isinstance(fout, HTTPError):
                if fout.code not in (429, 500, 502, 503, 504):
                    return None
                retry_after = fout.headers.get("Retry-After", "5")
                if retry_after.isdigit():
                    wachten = max(wachten, int(retry_after))
            time.sleep(wachten)


def herstel_tekst(tekst):
    try:
        return str(tekst).strip().encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return str(tekst).strip()


def normaal(tekst):
    """Vergelijk zonder hoofdletters, accenten en leestekens; versiewoorden blijven."""
    tekst = unicodedata.normalize("NFKD", herstel_tekst(tekst)).casefold()
    tekst = "".join(c for c in tekst if not unicodedata.combining(c))
    return re.sub(r"[^\w]+", "", tekst)


def sleutel(titel, artiest):
    return normaal(titel) + "|" + normaal(artiest)


def track_id(waarde):
    match = re.fullmatch(r"(?:spotify:track:|https://open.spotify.com/track/)?([A-Za-z0-9]{22})(?:\?[^\s]*)?", str(waarde).strip())
    return match.group(1) if match else None


def audio_voor_grafiek(df, cache):
    """Maak een grafiektabel met uitsluitend ReccoBeats-kenmerken."""
    nieuw = df.copy()
    nieuw["track_id"] = df["track_id"].map(track_id).fillna(df["Spotify ID"].map(track_id))
    for k in KENMERKEN:
        nieuw[k] = pd.to_numeric(nieuw["track_id"].map(lambda i: cache.get(i, {}).get(k)), errors="coerce")
    return nieuw


def aanvullen(origineel, opgeslagen):
    """fillna vult alleen lege plekken. Bestaande waarden en alle rijen blijven."""
    df = origineel.copy()
    genres = []
    for titel, artiest in df[["Nummer", "Artiest"]].itertuples(index=False, name=None):
        match = opgeslagen["itunes"].get(sleutel(titel, artiest), {})
        genres.append(match.get("genre") if match.get("status") == "Match" else None)
    df["track_genre"] = df["track_genre"].fillna(pd.Series(genres, index=df.index))
    df["Genrebron"] = pd.Series(pd.NA, index=df.index, dtype="string")
    df.loc[origineel["track_genre"].notna(), "Genrebron"] = "Spotify"
    df.loc[origineel["track_genre"].isna() & df["track_genre"].notna(), "Genrebron"] = "iTunes"

    audio = audio_voor_grafiek(origineel, opgeslagen["reccobeats"])
    toegevoegd = (origineel[KENMERKEN].isna() & audio[KENMERKEN].notna()).any(axis=1)
    df[KENMERKEN] = origineel[KENMERKEN].fillna(audio[KENMERKEN])
    df["Aanvulling audiobron"] = pd.Series(pd.NA, index=df.index, dtype="string")
    df.loc[toegevoegd, "Aanvulling audiobron"] = "ReccoBeats"
    df.loc[toegevoegd, "track_id"] = df.loc[toegevoegd, "track_id"].fillna(audio.loc[toegevoegd, "track_id"])
    return df


def ververs_genres(df, cache, voortgang):
    """Eén verzoek per ontbrekende titel/artiest; originele df niet dedupliceren."""
    nummers = df.loc[df["track_genre"].isna(), ["Nummer", "Artiest"]].dropna().copy()
    nummers["sleutel"] = [sleutel(t, a) for t, a in nummers.itertuples(index=False, name=None)]
    nummers = nummers.drop_duplicates("sleutel")
    nieuw = dict(cache)
    for i, (titel, artiest, key) in enumerate(nummers.itertuples(index=False, name=None), 1):
        url = "https://itunes.apple.com/search?" + urlencode({
            "term": f"{herstel_tekst(titel)} {herstel_tekst(artiest)}", "entity": "song", "country": "NL", "limit": 50})
        antwoord = ophalen(url)
        if antwoord is None or "results" not in antwoord:
            nieuw.setdefault(key, {"status": "API niet bereikbaar"})
        else:
            matches = [r for r in antwoord["results"] if r.get("primaryGenreName")
                       and normaal(r.get("trackName", "")) == normaal(titel)
                       and normaal(r.get("artistName", "")) == normaal(artiest)]
            record = {"status": "Geen eenduidige match", "genre": None, "zoek_url": url,
                      "opgehaald_op": datetime.now(timezone.utc).isoformat()}
            if len({r["primaryGenreName"] for r in matches}) == 1:
                match = min(matches, key=lambda r: r["trackId"])
                record.update(status="Match", genre=match["primaryGenreName"], titel=match["trackName"],
                              artiest=match["artistName"], itunes_id=match["trackId"], bron_url=match.get("trackViewUrl"))
            nieuw[key] = record
        voortgang(i, len(nummers))
        time.sleep(3.2)  # Minder dan circa twintig verzoeken per minuut.
    return nieuw


def ververs_audio(df, cache, voortgang):
    ids = df["track_id"].map(track_id).fillna(df["Spotify ID"].map(track_id)).dropna().unique().tolist()
    nieuw = dict(cache)
    for start in range(0, len(ids), 20):
        batch = ids[start:start + 20]
        url = "https://api.reccobeats.com/v1/audio-features?ids=" + ",".join(batch)
        antwoord = ophalen(url)
        if antwoord is None or "content" not in antwoord:
            for key in batch:
                nieuw.setdefault(key, {"status": "API niet bereikbaar"})
        else:
            # Koppelen op ID: de API kan antwoorden in een andere volgorde teruggeven.
            gevonden = {track_id(r.get("href")): r for r in antwoord["content"]}
            for key in batch:
                record = gevonden.get(key, {})
                waarden = {}
                for k in KENMERKEN:
                    v = record.get(k)
                    if isinstance(v, (int, float)) and pd.notna(v) and v >= 0 and (k == "tempo" or v <= 1):
                        waarden[k] = v
                nieuw[key] = {"status": "Match" if waarden else "Geen kenmerken gevonden", **waarden,
                              "bron_url": url, "opgehaald_op": datetime.now(timezone.utc).isoformat(),
                              "reccobeats_id": record.get("id")}
        voortgang(min(start + 20, len(ids)), len(ids))
        time.sleep(1)
    return nieuw
