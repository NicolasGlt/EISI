import tkinter as tk
import math
import threading
import time
import requests
import json
import websocket
import ssl
import hashlib
import yfinance as yf

# --- CONFIGURATION OFFICIELLE ROULETTE ---
# Ordre des numéros sur une roue européenne (Cylindre)
ROULETTE_SEQUENCE = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]
NB_SEGMENTS = len(ROULETTE_SEQUENCE)

def get_color(n):
    if n == 0: return "#27ae60"  # Vert pour le zéro
    # Liste des numéros rouges à la roulette
    reds = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
    return "#e74c3c" if n in reds else "#2c3e50" # Rouge ou Noir

# Couleurs générées selon la séquence
COLORS = [get_color(n) for n in ROULETTE_SEQUENCE]

data_shared = {
    "btc_price": None,
    "cac40_price": None
}

# --- LOGIQUE FLUX DE DONNÉES (THREADS) ---
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

def update_finance_data():
    """Met à jour le CAC40 en arrière-plan régulièrement"""
    while True:
        try:
            ticker = yf.Ticker("^FCHI")
            data_shared["cac40_price"] = ticker.fast_info['last_price']
        except: pass
        time.sleep(60) # Rafraîchissement toutes les minutes

# --- INTERFACE GRAPHIQUE ---
class RouletteEntropyCasino:
    def __init__(self, root):
        self.root = root
        self.root.title("Casino Entropy : BTC + CAC40 + ISS")
        self.root.geometry("500x750")
        self.root.configure(bg="#1a1a1a")
        
        self.canvas = tk.Canvas(root, width=500, height=550, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack()
        
        self.angle = 0
        self.spinning = False
        self.target_number = 0
        
        self.draw_wheel(0)
        
        # Flèche indicatrice
        self.canvas.create_polygon(240, 20, 260, 20, 250, 60, fill="#f1c40f", outline="white")
        
        self.btn = tk.Button(root, text="LANCER LE TIRAGE", command=self.start_spin, 
                             font=("Helvetica", 14, "bold"), bg="#f1c40f", fg="black", 
                             padx=30, pady=10, relief="flat", cursor="hand2")
        self.btn.pack(pady=20)
        
        self.result_label = tk.Label(root, text="EN ATTENTE D'ENTROPIE...", font=("Helvetica", 16, "bold"), 
                                     bg="#1a1a1a", fg="white")
        self.result_label.pack(pady=5)

    def draw_wheel(self, rotation):
        self.canvas.delete("segment")
        extent = 360 / NB_SEGMENTS
        
        for i, num in enumerate(ROULETTE_SEQUENCE):
            start_angle = rotation + (i * extent)
            color = COLORS[i]
            
            # Segment
            self.canvas.create_arc(50, 70, 450, 470, start=start_angle, extent=extent, 
                                   fill=color, tags="segment", outline="#34495e")
            
            # Numéro
            angle_rad = math.radians(start_angle + extent/2)
            txt_x = 250 + 170 * math.cos(angle_rad)
            txt_y = 270 - 170 * math.sin(angle_rad)
            
            self.canvas.create_text(txt_x, txt_y, text=str(num), fill="white", 
                                    font=("Arial", 10, "bold"), tags="segment", angle=start_angle+90)

    def get_entropy_result(self):
        """Technique d'entropie SHA-512 basée sur tes 3 sources"""
        try:
            # 1. ISS Position
            resp = requests.get("http://api.open-notify.org/iss-now.json", timeout=3).json()
            lat, lon = resp["iss_position"]["latitude"], resp["iss_position"]["longitude"]
            
            # 2. BTC & CAC40
            btc = data_shared["btc_price"] or 95000.0
            cac = data_shared["cac40_price"] or 7500.0
            
            # 3. Mélange SHA-512
            seed = f"{btc}{cac}{lat}{lon}{time.time_ns()}"
            hash_val = hashlib.sha512(seed.encode()).hexdigest()
            
            # Résultat modulo 37 (0 à 36)
            return int(hash_val, 16) % 37
        except Exception as e:
            print(f"Erreur Entropie: {e}")
            return int(time.time()) % 37

    def start_spin(self):
        if self.spinning: return
        
        self.spinning = True
        self.btn.config(state="disabled", bg="#7f8c8d")
        self.result_label.config(text="CALCUL DE L'ENTROPIE RÉELLE...", fg="#f1c40f")
        
        # Tirage du numéro via SHA-512
        self.target_number = self.get_entropy_result()
        
        # Calcul de l'angle pour s'arrêter sur le bon numéro
        # On cherche l'index du numéro gagnant dans notre séquence
        idx = ROULETTE_SEQUENCE.index(self.target_number)
        extent = 360 / NB_SEGMENTS
        
        # On veut que le segment visé soit en haut (90 degrés)
        # La formule prend en compte la position indexée
        angle_final_theorique = 90 - (idx * extent) - (extent / 2)
        
        self.start_angle = self.angle % 360
        # 6 tours complets + angle cible pour l'effet visuel
        self.final_angle = self.start_angle + (360 * 6) + (angle_final_theorique - self.start_angle)
        
        self.steps = 150 
        self.current_step = 0
        self.animate()

    def animate(self):
        if self.current_step <= self.steps:
            t = self.current_step / self.steps
            # Ralentissement progressif (Ease-out)
            power = 1 - pow(1 - t, 4)
            
            self.angle = self.start_angle + (self.final_angle - self.start_angle) * power
            self.draw_wheel(self.angle)
            
            self.current_step += 1
            self.root.after(25, self.animate)
        else:
            self.spinning = False
            self.btn.config(state="normal", bg="#f1c40f")
            color_res = get_color(self.target_number)
            self.result_label.config(text=f"RÉSULTAT : {self.target_number}", fg=color_res)

if __name__ == "__main__":
    # Lancement des collecteurs de données
    threading.Thread(target=run_kraken, daemon=True).start()
    threading.Thread(target=update_finance_data, daemon=True).start()
    
    root = tk.Tk()
    app = RouletteEntropyCasino(root)
    root.mainloop()