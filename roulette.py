
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

# --- CONFIGURATION ROULETTE ---
ROULETTE_SEQUENCE = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27,
                     13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33,
                     1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12,
                     35, 3, 26]

NB_SEGMENTS = len(ROULETTE_SEQUENCE)

def get_color(n):
    if n == 0:
        return "#27ae60"  
    reds = [1, 3, 5, 7, 9, 12, 14, 16, 18,
            19, 21, 23, 25, 27, 30, 32, 34, 36]
    return "#e74c3c" if n in reds else "#2c3e50"

COLORS = [get_color(n) for n in ROULETTE_SEQUENCE]

data_shared = {"btc_price": None, "cac40_price": None}

# --- THREADS KRAKEN ---
def on_message(ws, message):
    try:
        data = json.loads(message)
        if isinstance(data, list) and len(data) > 1:
            data_shared["btc_price"] = float(data[1]["c"][0])
    except:
        pass

def run_kraken():
    ws = websocket.WebSocketApp(
        "wss://ws.kraken.com",
        on_open=lambda ws: ws.send(json.dumps({
            "event": "subscribe",
            "pair": ["BTC/USD"],
            "subscription": {"name": "ticker"}
        })),
        on_message=on_message
    )
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

# --- THREADS CAC40 ---
def update_finance_data():
    while True:
        try:
            ticker = yf.Ticker("^FCHI")
            data_shared["cac40_price"] = ticker.fast_info["last_price"]
        except:
            pass
        time.sleep(60)

# --- INTERFACE ---
class RouletteEntropyCasino:
    def __init__(self, root):
        self.root = root
        self.root.title("Casino Entropy : BTC + CAC40 + ISS")
        self.root.geometry("950x650")
        self.root.configure(bg="#1a1a1a")

        self.bankroll = 100

        # --- FRAMES ---
        main_frame = tk.Frame(root, bg="#1a1a1a")
        main_frame.pack(fill="both", expand=True)

        left_frame = tk.Frame(main_frame, bg="#1a1a1a")
        left_frame.grid(row=0, column=0, padx=30, sticky="n")

        center_frame = tk.Frame(main_frame, bg="#1a1a1a")
        center_frame.grid(row=0, column=1, pady=10)

        right_frame = tk.Frame(main_frame, bg="#1a1a1a")
        right_frame.grid(row=0, column=2, padx=40, sticky="n")

        # --- ROULETTE ---
        self.canvas = tk.Canvas(center_frame, width=500, height=550,
                                bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack()
        self.angle = 0
        self.spinning = False
        self.target_number = 0

        self.draw_wheel(0)
        self.canvas.create_polygon(240, 20, 260, 20, 250, 60,
                                   fill="#f1c40f", outline="white")

        # --- BOUTON LANCER ---
        self.btn = tk.Button(left_frame, text="LANCER",
                             command=self.start_spin,
                             font=("Helvetica", 18, "bold"),
                             bg="#f1c40f", fg="black",
                             padx=30, pady=30)
        self.btn.pack(pady=10)

        # --- BANKROLL ---
        self.money_label = tk.Label(right_frame,
                                    text=f"ARGENT : {self.bankroll} €",
                                    font=("Helvetica", 18, "bold"),
                                    bg="#1a1a1a", fg="#2ecc71")
        self.money_label.pack(pady=10)

        # --- TYPE DE MISE ---
        tk.Label(right_frame, text="Type de pari :", bg="#1a1a1a",
                 fg="white", font=("Helvetica", 14)).pack()
        self.bet_type = tk.StringVar(value="Rouge")
        tk.OptionMenu(right_frame, self.bet_type,
                      "Rouge", "Noir", "Vert", "Numéro").pack(pady=5)

        # --- MONTANT ---
        tk.Label(right_frame, text="Mise (€) :", bg="#1a1a1a",
                 fg="white", font=("Helvetica", 14)).pack()
        self.bet_amount = tk.Entry(right_frame)
        self.bet_amount.pack(pady=5)
        self.bet_amount.bind("<KeyRelease>", self.check_bet_validity)

        # --- NUMÉRO ---
        tk.Label(right_frame, text="Numéro (si pari numéro) :",
                 bg="#1a1a1a", fg="white", font=("Helvetica", 14)).pack()
        self.bet_number_entry = tk.Entry(right_frame)
        self.bet_number_entry.pack(pady=5)

        # --- RECAP GAINS ---
        recap = (
            "📌 Gains possibles :\n"
            "• Rouge / Noir → x2\n"
            "• Vert (0) → x14\n"
            "• Numéro → x36"
        )
        self.recap_label = tk.Label(right_frame, text=recap,
                                    bg="#1a1a1a", fg="#f1c40f",
                                    font=("Helvetica", 12), justify="left")
        self.recap_label.pack(pady=20)

        # --- RESULTAT ---
        self.result_label = tk.Label(center_frame,
                                     text="EN ATTENTE D'ENTROPIE...",
                                     font=("Helvetica", 16, "bold"),
                                     bg="#1a1a1a", fg="white")
        self.result_label.pack(pady=10)

    # --- VERIFICATION MISE ---
    def check_bet_validity(self, event=None):
        try:
            bet = int(self.bet_amount.get())
            if bet <= 0 or bet > self.bankroll:
                self.btn.config(state="disabled")
            else:
                self.btn.config(state="normal")
        except:
            self.btn.config(state="disabled")

    # --- ROULETTE ---
    def draw_wheel(self, rotation):
        self.canvas.delete("segment")
        extent = 360 / NB_SEGMENTS

        for i, num in enumerate(ROULETTE_SEQUENCE):
            start_angle = rotation + i * extent
            color = COLORS[i]

            self.canvas.create_arc(50, 70, 450, 470,
                                   start=start_angle, extent=extent,
                                   fill=color, outline="#34495e",
                                   tags="segment")

            angle_rad = math.radians(start_angle + extent/2)
            x = 250 + 170 * math.cos(angle_rad)
            y = 270 - 170 * math.sin(angle_rad)

            self.canvas.create_text(x, y, text=str(num), fill="white",
                                    font=("Arial", 10, "bold"),
                                    tags="segment", angle=start_angle + 90)

    # --- ENTROPIE SHA-512 ---
    def get_entropy_result(self):
        try:
            resp = requests.get("http://api.open-notify.org/iss-now.json", timeout=3).json()

            lat = resp["iss_position"]["latitude"]
            lon = resp["iss_position"]["longitude"]
            btc = data_shared["btc_price"]
            cac = data_shared["cac40_price"]

            seed = f"{btc}{cac}{lat}{lon}{time.time_ns()}"
            h = hashlib.sha512(seed.encode()).hexdigest()
            return int(h, 16) % 37
        except:
            return int(time.time()) % 37

    # --- PARI ---
    def resolve_bet(self):
        bet_type = self.bet_type.get()
        try:
            bet = int(self.bet_amount.get())
        except:
            self.result_label.config(text="Mise invalide", fg="red")
            return

        if bet > self.bankroll:
            self.result_label.config(text="Mise trop élevée !", fg="red")
            return

        self.bankroll -= bet
        gain = 0
        win = False

        if bet_type == "Rouge" and get_color(self.target_number) == "#e74c3c":
            win, gain = True, bet * 2

        elif bet_type == "Noir" and get_color(self.target_number) == "#2c3e50":
            win, gain = True, bet * 2

        elif bet_type == "Vert" and self.target_number == 0:
            win, gain = True, bet * 14

        elif bet_type == "Numéro":
            try:
                num = int(self.bet_number_entry.get())
                if num == self.target_number:
                    win, gain = True, bet * 36
            except:
                self.result_label.config(text="Numéro invalide", fg="red")
                return

        if win:
            self.bankroll += gain
            self.result_label.config(
                text=f"RÉSULTAT : {self.target_number} — GAGNÉ +{gain}€",
                fg="#2ecc71"
            )
        else:
            self.result_label.config(
                text=f"RÉSULTAT : {self.target_number} — PERDU",
                fg="#e74c3c"
            )

        self.money_label.config(text=f"ARGENT : {self.bankroll} €")
        self.check_bet_validity()

    # --- SPIN ---
    def start_spin(self):
        if self.spinning:
            return

        self.spinning = True
        self.btn.config(state="disabled")
        self.result_label.config(text="CALCUL ENTROPIE...", fg="#f1c40f")

        self.target_number = self.get_entropy_result()

        idx = ROULETTE_SEQUENCE.index(self.target_number)
        extent = 360 / NB_SEGMENTS
        target_angle = 90 - (idx * extent) - (extent / 2)

        self.start_angle = self.angle % 360
        self.final_angle = self.start_angle + 360*6 + (target_angle - self.start_angle)

        self.steps = 150
        self.current_step = 0

        self.animate()

    def animate(self):
        if self.current_step <= self.steps:
            t = self.current_step / self.steps
            accel = 1 - pow(1 - t, 4)
            self.angle = self.start_angle + (self.final_angle - self.start_angle) * accel

            self.draw_wheel(self.angle)
            self.current_step += 1
            self.root.after(20, self.animate)
        else:
            self.spinning = False
            self.resolve_bet()
            self.check_bet_validity()

# --- MAIN ---
if __name__ == "__main__":
    threading.Thread(target=run_kraken, daemon=True).start()
    threading.Thread(target=update_finance_data, daemon=True).start()

    root = tk.Tk()
    app = RouletteEntropyCasino(root)
    root.mainloop()
