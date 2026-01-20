import tkinter as tk
import math
import threading
import time
import requests
import json
import websocket
import ssl
import hashlib

# --- CONFIGURATION ---
NB_SEGMENTS = 37  # Nombres de 1 à 37
# Couleurs style casino (Rouge, Noir, et le 37 en Vert)
COLORS = ["#e74c3c", "#2c3e50"] * 18 + ["#27ae60"]

data_shared = {"btc_price": None}

# --- LOGIQUE KRAKEN (THREAD SÉPARÉ) ---
def on_message(ws, message):
    try:
        data = json.loads(message)
        if isinstance(data, list) and len(data) > 1:
            ticker = data[1]
            data_shared["btc_price"] = float(ticker["c"][0])
    except:
        pass

def run_kraken():
    websocket_url = "wss://ws.kraken.com"
    ws = websocket.WebSocketApp(
        websocket_url,
        on_open=lambda ws: ws.send(json.dumps({
            "event": "subscribe", 
            "pair": ["BTC/USD"],
            "subscription": {"name": "ticker"}
        })),
        on_message=on_message
    )
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

# --- INTERFACE GRAPHIQUE ---
class RouletteEISI:
    def __init__(self, root):
        self.root = root
        self.root.title("Roulette Entropy System (BTC & ISS)")
        self.root.geometry("500x700")
        
        # Canvas pour la roue
        self.canvas = tk.Canvas(root, width=500, height=550, bg="white", highlightthickness=0)
        self.canvas.pack()
        
        self.angle = 0
        self.spinning = False
        self.target_number = 1
        
        # Initialisation du dessin
        self.draw_wheel(0)
        
        # Curseur indicateur (Flèche noire en haut)
        self.canvas.create_polygon(240, 20, 260, 20, 250, 50, fill="black")
        
        # Interface de contrôle
        self.btn = tk.Button(root, text="LANCER LA ROUE", command=self.start_spin, 
                             font=("Arial", 14, "bold"), bg="#27ae60", fg="white", 
                             padx=30, pady=10, cursor="hand2")
        self.btn.pack(pady=10)
        
        self.result_label = tk.Label(root, text="Prêt pour le tirage", font=("Arial", 16, "bold"))
        self.result_label.pack(pady=5)

    def draw_wheel(self, rotation):
        self.canvas.delete("segment")
        extent = 360 / NB_SEGMENTS
        
        for i in range(NB_SEGMENTS):
            # Calcul de l'angle pour chaque part
            start_angle = rotation + (i * extent)
            color = COLORS[i % len(COLORS)]
            
            # Dessin de la part de gâteau
            self.canvas.create_arc(50, 60, 450, 460, start=start_angle, extent=extent, 
                                   fill=color, tags="segment", outline="#ecf0f1")
            
            # Placement du numéro
            angle_rad = math.radians(start_angle + extent/2)
            # 250, 260 est le centre de la roue
            txt_x = 250 + 175 * math.cos(angle_rad)
            txt_y = 260 - 175 * math.sin(angle_rad)
            
            self.canvas.create_text(txt_x, txt_y, text=str(i+1), fill="white", 
                                    font=("Arial", 11, "bold"), tags="segment")

    def get_entropy_result(self):
        """Calcule le nombre final basé sur l'entropie réelle"""
        try:
            # Source 1: ISS
            resp = requests.get("http://api.open-notify.org/iss-now.json", timeout=3).json()
            lat = float(resp["iss_position"]["latitude"])
            lon = float(resp["iss_position"]["longitude"])
            
            # Source 2: BTC (via Kraken)
            btc = data_shared["btc_price"] or 90000.0
            
            # Source 3: SHA-256 pour mélanger parfaitement
            seed = f"{btc}{lat}{lon}{time.time_ns()}"
            hash_val = hashlib.sha256(seed.encode()).hexdigest()
            
            # Résultat entre 1 et 37
            return (int(hash_val, 16) % 37) + 1
        except:
            return 1 # Fallback si internet coupe

    def start_spin(self):
        if self.spinning: return
        
        self.spinning = True
        self.btn.config(state="disabled", bg="#95a5a6")
        self.result_label.config(text="Extraction de l'entropie...", fg="black")
        
        # Calcul du numéro gagnant AVANT de commencer
        self.target_number = self.get_entropy_result()
        
        # Calcul de l'angle de destination
        # Le haut du canvas est à 90°. 
        # On calcule où doit être le zéro de la roue pour que target soit à 90°.
        extent = 360 / NB_SEGMENTS
        angle_final_theorique = 90 - ((self.target_number - 1) * extent) - (extent / 2)
        
        # Paramètres de l'animation
        self.start_angle = self.angle % 360
        # On fait 5 tours complets + l'angle cible
        self.final_angle = self.start_angle + (360 * 5) + (angle_final_theorique - self.start_angle)
        
        self.steps = 120  # Durée (environ 3-4 secondes)
        self.current_step = 0
        self.animate()

    def animate(self):
        if self.current_step <= self.steps:
            # Fonction Ease-Out (ralentissement progressif fluide)
            t = self.current_step / self.steps
            # Formule cubique pour un arrêt très doux
            ease_out = 1 - pow(1 - t, 3)
            
            self.angle = self.start_angle + (self.final_angle - self.start_angle) * ease_out
            self.draw_wheel(self.angle)
            
            self.current_step += 1
            self.root.after(30, self.animate)
        else:
            self.spinning = False
            self.btn.config(state="normal", bg="#27ae60")
            self.result_label.config(text=f"RÉSULTAT : {self.target_number}", fg="#c0392b")

# --- EXECUTION ---
if __name__ == "__main__":
    # Démarrage du flux Kraken en arrière-plan
    threading.Thread(target=run_kraken, daemon=True).start()
    
    # Lancement de la fenêtre Tkinter
    root = tk.Tk()
    # Centrer la fenêtre
    root.eval('tk::PlaceWindow . center')
    app = RouletteEISI(root)
    root.mainloop()