import websocket
import json
import ssl
import requests
import time
import threading
import matplotlib.pyplot as plt
import hashlib
import yfinance as yf # Pour le CAC40

# --- PARAMÈTRES ---
NB_GENERATIONS_CIBLE = 1000 
BATCH_SIZE = 50 
VALEUR_MAX = 37 # Pour obtenir 0 à 36

data_shared = {
    "btc_price": None,
    "cac40_price": None,
    "iss_lat": None,
    "iss_lon": None
}
resultats_entropie = []

# --- 1. SOURCE BTC (KRAKEN WS) ---
def on_message(ws, message):
    try:
        data = json.loads(message)
        if isinstance(data, list) and len(data) > 1:
            data_shared["btc_price"] = float(data[1]["c"][0])
    except: pass

def run_kraken():
    ws = websocket.WebSocketApp("wss://ws.kraken.com", 
        on_open=lambda ws: ws.send(json.dumps({"event":"subscribe", "pair":["BTC/USD"], "subscription":{"name":"ticker"}})),
        on_message=on_message)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

# --- 2. SOURCE CAC40 (YFINANCE) ---
def update_cac40():
    try:
        # ^FCHI est le symbole du CAC40
        ticker = yf.Ticker("^FCHI")
        price = ticker.fast_info['last_price']
        data_shared["cac40_price"] = price
    except: pass

# --- 3. GÉNÉRATION SHA-512 ---
def generer_batch(btc, cac, lat, lon, size):
    batch = []
    for i in range(size):
        # Nouvelle formule : BTC + CAC40 + ISS + TEMPS
        seed = f"{btc}{cac}{lat}{lon}{time.time_ns()}{i}"
        hash_val = hashlib.sha512(seed.encode()).hexdigest()
        nombre = int(hash_val, 16) % VALEUR_MAX
        batch.append(nombre)
    return batch

# --- 4. BOUCLE PRINCIPALE ---
def run_logic():
    ISS_URL = "http://api.open-notify.org/iss-now.json"
    print(f"Collecte en cours (BTC + CAC40 + ISS)...")

    while len(resultats_entropie) < NB_GENERATIONS_CIBLE:
        try:
            # Update ISS et CAC40 (environ toutes les secondes)
            update_cac40()
            iss_resp = requests.get(ISS_URL, timeout=5).json()
            
            if iss_resp["message"] == "success":
                data_shared["iss_lat"] = float(iss_resp["iss_position"]["latitude"])
                data_shared["iss_lon"] = float(iss_resp["iss_position"]["longitude"])

            # On vérifie qu'on a toutes les données
            d = data_shared
            if all([d["btc_price"], d["cac40_price"], d["iss_lat"]]):
                nouveaux = generer_batch(d["btc_price"], d["cac40_price"], d["iss_lat"], d["iss_lon"], BATCH_SIZE)
                resultats_entropie.extend(nouveaux)
                print(f"Points : {len(resultats_entropie)}/{NB_GENERATIONS_CIBLE}")
            
            time.sleep(1)
        except Exception as e:
            time.sleep(2)

    afficher_analyses()

# --- 5. VISUALISATION (3 TABLEAUX) ---
def afficher_analyses():
    fig, axs = plt.subplots(1, 3, figsize=(18, 5))
    
    # Graphique 0 : Nuage de points
    axs[0].scatter(range(len(resultats_entropie)), resultats_entropie, s=10, alpha=0.5, color='red')
    axs[0].set_title("1. Nuage de points (Entropie)")
    axs[0].set_ylim(-1, 37)
    axs[0].set_ylabel("Valeur (0-36)")

    # Graphique 1 : Histogramme
    axs[1].hist(resultats_entropie, bins=range(38), color='skyblue', edgecolor='black', alpha=0.7)
    axs[1].set_title("2. Fréquence (Histogramme)")
    axs[1].set_xlabel("Chiffre")
    axs[1].set_ylabel("Nombre d'apparitions")

    # Graphique 2 : Trié
    axs[2].plot(sorted(resultats_entropie), color='green', linewidth=2)
    axs[2].set_title("3. Distribution triée")
    axs[2].set_xlabel("Nombre de tirages")
    axs[2].set_ylabel("Valeur")

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    threading.Thread(target=run_kraken, daemon=True).start()
    run_logic()