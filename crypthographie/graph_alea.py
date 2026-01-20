import websocket
import json
import ssl
import requests
import time
import threading
import matplotlib.pyplot as plt
import hashlib

# --- Paramètres ---
NB_GENERATIONS_CIBLE = 1000
BATCH_SIZE = 50 
data_shared = {
    "btc_price": None,
    "iss_lat": None,
    "iss_lon": None
}
resultats_entropie = []
timestamps = [] # Pour l'axe X du graphique

# --- Logique Kraken (WebSocket) ---
def on_message(ws, message):
    try:
        data = json.loads(message)
        if isinstance(data, list) and len(data) > 1:
            ticker = data[1]
            data_shared["btc_price"] = float(ticker["c"][0])
    except:
        pass

def run_kraken():
    ws = websocket.WebSocketApp("wss://ws.kraken.com", 
                                on_open=lambda ws: ws.send(json.dumps({
                                    "event": "subscribe", "pair": ["BTC/USD"],
                                    "subscription": {"name": "ticker"}
                                })),
                                on_message=on_message)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

# --- Génération avec maximum de "Bruit" ---
def generer_batch(btc, lat, lon, size):
    batch = []
    for i in range(size):
        # On crée une graine unique par point
        # On mélange : Prix + Lat + Lon + Nanosecondes + Index
        seed = f"{btc}{lat}{lon}{time.time_ns()}{i}{hash(time.time())}"
        
        # Hachage SHA-512 pour une dispersion maximale
        hash_val = hashlib.sha512(seed.encode()).hexdigest()
        
        # Transformation en nombre entre 0 et 37
        nombre = int(hash_val, 16) % 38
        batch.append(nombre)
    return batch

def run_entropy_logic():
    ISS_URL = "http://api.open-notify.org/iss-now.json"
    print(f"Collecte de {NB_GENERATIONS_CIBLE} points en cours...")

    while len(resultats_entropie) < NB_GENERATIONS_CIBLE:
        try:
            response = requests.get(ISS_URL, timeout=5)
            iss_data = response.json()
            
            if iss_data["message"] == "success":
                data_shared["iss_lat"] = float(iss_data["iss_position"]["latitude"])
                data_shared["iss_lon"] = float(iss_data["iss_position"]["longitude"])

            btc = data_shared["btc_price"]
            lat = data_shared["iss_lat"]
            lon = data_shared["iss_lon"]

            if btc and lat and lon:
                nouveaux = generer_batch(btc, lat, lon, BATCH_SIZE)
                resultats_entropie.extend(nouveaux)
                print(f"Points générés : {len(resultats_entropie)}/1000")
            
            time.sleep(0.5) # On accélère un peu la boucle

        except Exception:
            time.sleep(1)

    afficher_graphique_points()

# --- Nouveau Graphique par Points ---
def afficher_graphique_points():
    plt.figure(figsize=(12, 6))
    
    # Création de l'axe X (1, 2, 3... 1000)
    indices = range(len(resultats_entropie))
    
    # Dessin des points
    # 's=10' pour la taille des points, 'alpha=0.6' pour la transparence
    plt.scatter(indices, resultats_entropie, s=15, c='red', alpha=0.5, edgecolors='none')
    
    plt.title(f"Nuage de points d'entropie (1000 tirages)\nSource : BTC + ISS + SHA-512")
    plt.xlabel("Ordre de génération (Temps)")
    plt.ylabel("Valeur générée (0-37)")
    
    # On force l'affichage de 0 à 37 sur l'axe Y
    plt.ylim(-1, 38)
    plt.yticks(range(0, 39, 2))
    
    plt.grid(True, which='both', linestyle='--', alpha=0.3)
    
    print("\nGraphique affiché. Observez la répartition des points !")
    plt.show()

if __name__ == "__main__":
    thread_kraken = threading.Thread(target=run_kraken, daemon=True)
    thread_kraken.start()
    run_entropy_logic()