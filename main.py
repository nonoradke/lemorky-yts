from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import urllib.parse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIG ---
# ✅ PAKE URL YANG SUKSES DI SCANNER TADI
YTS_API_URL = "https://yts.lt/api/v2/list_movies.json"

# List Trackers (Biar downloadnya ngebut parah)
TRACKERS = [
    "udp://open.demonii.com:1337/announce",
    "udp://tracker.openbittorrent.com:80",
    "udp://tracker.coppersurfer.tk:6969",
    "udp://glotorrents.pw:6969/announce",
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://torrent.gresille.org:80/announce",
    "udp://p4p.arenabg.com:1337",
    "udp://tracker.leechers-paradise.org:6969"
]

@app.get("/manifest.json")
def get_manifest():
    return {
        "id": "org.lemorky.yts",
        "version": "1.0.0",
        "name": "Lemorky YTS",
        "description": "Special 4K/1080p Movies from YTS.LT",
        "types": ["movie"],
        "catalogs": [],
        "resources": ["stream"],
        "idPrefixes": ["tt"]
    }

@app.get("/stream/{type}/{id}.json")
def get_stream(type: str, id: str):
    # 1. Reject kalo bukan Movie (Hemat Resource)
    if type != "movie":
        return {"streams": []}

    # Ambil IMDb ID (contoh: tt1234567)
    imdb_id = id.split(":")[0]
    
    print(f"🔍 Mencari Film di YTS: {imdb_id}")

    try:
        # Request ke API YTS pake IMDb ID
        params = {
            "query_term": imdb_id
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        }

        # Timeout 10 detik cukup
        resp = requests.get(YTS_API_URL, params=params, headers=headers, timeout=10)
        data = resp.json()

        # Cek apakah filmnya ketemu
        if data.get('status') != 'ok' or data.get('data', {}).get('movie_count', 0) == 0:
            print("❌ Film tidak ditemukan di database YTS")
            return {"streams": []}

        # Ambil data movie
        movie = data['data']['movies'][0]
        title_long = movie.get('title_long', movie.get('title'))
        torrents = movie.get('torrents', [])

        streams = []

        # Loop varian kualitas
        for t in torrents:
            quality = t.get('quality', 'Unknown')
            type_res = t.get('type', '') # bluray / web
            size = t.get('size', '??')
            seeds = t.get('seeds', 0)
            info_hash = t.get('hash')
            
            # Skip kalo hash gak ada
            if not info_hash: continue

            # Rakit Magnet Link Manual
            encoded_title = urllib.parse.quote(title_long)
            magnet_link = f"magnet:?xt=urn:btih:{info_hash}&dn={encoded_title}"
            
            for tr in TRACKERS:
                magnet_link += f"&tr={tr}"

            # Format Tampilan di Stremio
            streams.append({
                "name": f"YTS {quality}",
                "title": f"{title_long}\n💾 {size} | 👤 {seeds} Seeds | {type_res.upper()}",
                "infoHash": info_hash,
                "behaviorHints": {
                    "bingeGroup": f"yts-{quality}"
                }
            })
        
        return {"streams": streams}

    except Exception as e:
        print(f"🔥 Error: {e}")
        return {"streams": []}
