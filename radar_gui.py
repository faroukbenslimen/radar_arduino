import threading
import time
import math
import serial
import tkinter as tk
from tkinter import ttk, messagebox

# Simple Tkinter radar GUI that reads serial lines in format: angle,distance.
# Usage: python radar_gui.py

WIDTH = 900
HEIGHT = 600
RADAR_RADIUS = 400
MAX_DISTANCE = 20.0  # cm

class RadarGUI:
    def __init__(self, master):
        self.master = master
        master.title("Professional Radar System")
        master.configure(bg="#0a0e27")
        self.canvas = tk.Canvas(master, width=WIDTH, height=HEIGHT, bg="#0a0e27", highlightthickness=0)
        self.canvas.pack(pady=10)

        controls = tk.Frame(master, bg="#0a0e27")
        controls.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(controls, text="Port:", bg="#0a0e27", fg="#00d4ff", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.port_var = tk.StringVar(value="COM3")
        tk.Entry(controls, textvariable=self.port_var, width=8, bg="#1a1e37", fg="#00d4ff", insertbackground="#00d4ff", relief=tk.FLAT, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        tk.Label(controls, text="Baud:", bg="#0a0e27", fg="#00d4ff", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.baud_var = tk.IntVar(value=9600)
        tk.Entry(controls, textvariable=self.baud_var, width=6, bg="#1a1e37", fg="#00d4ff", insertbackground="#00d4ff", relief=tk.FLAT, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

        self.connect_btn = tk.Button(controls, text="CONNECT", command=self.toggle_connect, bg="#00d4ff", fg="#0a0e27", font=("Arial", 10, "bold"), relief=tk.FLAT, padx=15, cursor="hand2")
        self.connect_btn.pack(side=tk.LEFT, padx=15)

        self.status_lbl = tk.Label(controls, text="● DISCONNECTED", fg="#ff4444", bg="#0a0e27", font=("Arial", 10, "bold"))
        self.status_lbl.pack(side=tk.LEFT, padx=10)

        # Radar state
        self.center_x = WIDTH / 2
        self.center_y = HEIGHT - 80
        self.sweep_angle = 0
        self.sweep_direction = 1  # 1 for forward, -1 for backward
        self.current_angle = 0
        self.current_distance = 0
        self.point_history = []  # list of (x,y,age)

        self.ser = None
        self._stop_event = threading.Event()
        self._thread = None

        # Start UI update loop
        self._draw_static()
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_loop()

    def _draw_static(self):
        self.canvas.delete("static")
        # Draw concentric arcs (4 rings for better detail)
        for i in range(1, 5):
            r = i * (RADAR_RADIUS / 4.0)
            x0, y0 = self.center_x - r, self.center_y - r
            x1, y1 = self.center_x + r, self.center_y + r
            self.canvas.create_arc(x0, y0, x1, y1, start=0, extent=180, style=tk.ARC, outline="#1a4d4d", width=1, tags="static")
        # Base line
        self.canvas.create_line(self.center_x - RADAR_RADIUS, self.center_y, self.center_x + RADAR_RADIUS, self.center_y, fill="#00d4ff", width=2, tags="static")
        # Radial lines every 30 degrees (0-180)
        for i in range(7):
            ang = math.radians(i * 30)
            x2 = self.center_x + RADAR_RADIUS * math.cos(ang)
            y2 = self.center_y - RADAR_RADIUS * math.sin(ang)
            self.canvas.create_line(self.center_x, self.center_y, x2, y2, fill="#1a4d4d", width=1, tags="static")
        # Angle labels
        for i in range(7):
            ang = i * 30
            rad = math.radians(ang)
            x = self.center_x + (RADAR_RADIUS + 25) * math.cos(rad)
            y = self.center_y - (RADAR_RADIUS + 25) * math.sin(rad)
            self.canvas.create_text(x, y, text=f"{ang}°", fill="#00d4ff", font=("Arial", 9, "bold"), tags="static")
        # Distance labels
        for i in range(1, 5):
            r = i * (RADAR_RADIUS / 4.0)
            self.canvas.create_text(self.center_x + r + 5, self.center_y - 10, text=f"{int(i*5)}cm", fill="#1a9999", font=("Arial", 8), tags="static")

    def toggle_connect(self):
        if self.ser:
            self._stop_serial_thread()
        else:
            self._start_serial_thread()

    def _start_serial_thread(self):
        port = self.port_var.get()
        baud = int(self.baud_var.get())
        try:
            self.ser = serial.Serial(port, baud, timeout=1)
            time.sleep(1)
        except Exception as e:
            messagebox.showerror("Serial Error", str(e))
            self.ser = None
            return
        self.status_lbl.config(text=f"● CONNECTED ({port})", fg="#00ff88")
        self.connect_btn.config(text="DISCONNECT", bg="#ff4444")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._serial_loop, daemon=True)
        self._thread.start()

    def _stop_serial_thread(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1)
        try:
            if self.ser:
                self.ser.close()
        except Exception:
            pass
        self.ser = None
        self.status_lbl.config(text="● DISCONNECTED", fg="#ff4444")
        self.connect_btn.config(text="CONNECT", bg="#00d4ff")

    def _serial_loop(self):
        while not self._stop_event.is_set():
            try:
                if self.ser and self.ser.in_waiting:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if not line:
                        continue
                    # Expecting angle,distance. or angle,distance
                    if line.endswith('.'):
                        line = line[:-1]
                    parts = line.split(',')
                    if len(parts) >= 2:
                        try:
                            ang = float(parts[0])
                            dist = float(parts[1])
                            self.current_angle = ang
                            self.current_distance = dist
                            self._add_point_from(ang, dist)
                        except ValueError:
                            pass
                else:
                    time.sleep(0.02)
            except Exception:
                time.sleep(0.2)

    def _add_point_from(self, angle, distance):
        if distance <= 0 or distance > MAX_DISTANCE or angle < 0 or angle > 180:
            return
        rad = math.radians(angle)
        mapped = (distance / MAX_DISTANCE) * RADAR_RADIUS
        x = self.center_x + mapped * math.cos(rad)
        y = self.center_y - mapped * math.sin(rad)
        self.point_history.append([x, y, 255])

    def update_loop(self):
        self.canvas.delete("dynamic")
        
        # Sweep line (0-180 degrees back and forth)
        if self.ser:
            sweep_angle = self.current_angle
        else:
            self.sweep_angle += self.sweep_direction * 1
            if self.sweep_angle >= 180:
                self.sweep_angle = 180
                self.sweep_direction = -1
            elif self.sweep_angle <= 0:
                self.sweep_angle = 0
                self.sweep_direction = 1
            sweep_angle = self.sweep_angle
        
        rad = math.radians(sweep_angle)
        ex = self.center_x + RADAR_RADIUS * math.cos(rad)
        ey = self.center_y - RADAR_RADIUS * math.sin(rad)
        self.canvas.create_line(self.center_x, self.center_y, ex, ey, fill="#00ff88", width=2, tags="dynamic")
        
        # Sweep fade effect
        for offset in range(1, 15):
            fade_angle = (sweep_angle - offset) % 181
            rad_f = math.radians(fade_angle)
            ex_f = self.center_x + RADAR_RADIUS * math.cos(rad_f)
            ey_f = self.center_y - RADAR_RADIUS * math.sin(rad_f)
            alpha = 255 - (offset * 17)
            color = f"#00{alpha//4:02x}{alpha//4:02x}"
            self.canvas.create_line(self.center_x, self.center_y, ex_f, ey_f, fill=color, width=1, tags="dynamic")
        
        # Current detection point
        if 0 < self.current_distance <= MAX_DISTANCE and 0 <= self.current_angle <= 180:
            rad_c = math.radians(self.current_angle)
            mapped_dist = (self.current_distance / MAX_DISTANCE) * RADAR_RADIUS
            px = self.center_x + mapped_dist * math.cos(rad_c)
            py = self.center_y - mapped_dist * math.sin(rad_c)
            self.canvas.create_oval(px-5, py-5, px+5, py+5, fill="#ff3366", outline="#ff6699", width=2, tags="dynamic")
        
        # History trail
        new_hist = []
        for p in self.point_history:
            alpha = int(p[2])
            if alpha <= 0:
                continue
            color = f"#{alpha//3:02x}{alpha:02x}{alpha//2:02x}"
            self.canvas.create_oval(p[0]-2, p[1]-2, p[0]+2, p[1]+2, fill=color, outline="", tags="dynamic")
            p[2] -= 3
            if p[2] > 0:
                new_hist.append(p)
        self.point_history = new_hist
        
        # Professional HUD
        self.canvas.create_text(WIDTH/2, 30, text="RADAR SYSTEM", fill="#00d4ff", font=("Arial", 22, "bold"), tags="dynamic")
        self.canvas.create_rectangle(30, 60, 250, 140, outline="#00d4ff", width=2, tags="dynamic")
        self.canvas.create_text(140, 75, text="TELEMETRY", fill="#00d4ff", font=("Arial", 10, "bold"), tags="dynamic")
        self.canvas.create_text(50, 100, anchor=tk.W, text=f"ANGLE:", fill="#1a9999", font=("Arial", 11, "bold"), tags="dynamic")
        self.canvas.create_text(180, 100, anchor=tk.E, text=f"{self.current_angle:.1f}°", fill="#00ff88", font=("Arial", 12, "bold"), tags="dynamic")
        self.canvas.create_text(50, 125, anchor=tk.W, text=f"RANGE:", fill="#1a9999", font=("Arial", 11, "bold"), tags="dynamic")
        self.canvas.create_text(180, 125, anchor=tk.E, text=f"{self.current_distance:.1f} cm", fill="#00ff88", font=("Arial", 12, "bold"), tags="dynamic")
        
        self.master.after(30, self.update_loop)

    def on_close(self):
        self._stop_serial_thread()
        self.master.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app = RadarGUI(root)
    root.mainloop()
