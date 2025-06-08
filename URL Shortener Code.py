import sys
import tkinter as tk
from tkinter import messagebox
import sqlite3
import string
import random
import os
import argparse
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import math

DATABASE = 'urls.db'
HOST_URL = 'http://127.0.0.1:8000/'

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS urls 
                    (short_code TEXT PRIMARY KEY, original_url TEXT, clicks INTEGER DEFAULT 0)''')
        conn.commit()

def generate_short_code():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(6))

def shorten_url(original_url):
    if not original_url:
        return None, "URL is required"
    
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        while True:
            short_code = generate_short_code()
            c.execute('SELECT short_code FROM urls WHERE short_code = ?', (short_code,))
            if not c.fetchone():
                break
        
        c.execute('INSERT INTO urls (short_code, original_url) VALUES (?, ?)', 
                 (short_code, original_url))
        conn.commit()
        
        return f"{HOST_URL}{short_code}", None

class AnimatedBackground:
    def __init__(self, canvas, width, height):
        self.canvas = canvas
        self.width = width
        self.height = height
        self.dots = []
        self.num_dots = 50
        self.max_distance = 150
        self.dot_radius = 2
        self.dot_speed = 1
        
        for _ in range(self.num_dots):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            vx = random.uniform(-self.dot_speed, self.dot_speed)
            vy = random.uniform(-self.dot_speed, self.dot_speed)
            dot = self.canvas.create_oval(x - self.dot_radius, y - self.dot_radius,
                                        x + self.dot_radius, y + self.dot_radius,
                                        fill="white", outline="white")
            self.dots.append({'id': dot, 'x': x, 'y': y, 'vx': vx, 'vy': vy})
        
        self.lines = []
        self.animate()

    def animate(self):
        for dot in self.dots:
            dot['x'] += dot['vx']
            dot['y'] += dot['vy']
            
            if dot['x'] < 0 or dot['x'] > self.width:
                dot['vx'] *= -1
            if dot['y'] < 0 or dot['y'] > self.height:
                dot['vy'] *= -1
            
            self.canvas.coords(dot['id'], dot['x'] - self.dot_radius, dot['y'] - self.dot_radius,
                             dot['x'] + self.dot_radius, dot['y'] + self.dot_radius)
        
        for line in self.lines:
            self.canvas.delete(line)
        self.lines = []
        
        for i, dot1 in enumerate(self.dots):
            for dot2 in self.dots[i + 1:]:
                distance = math.sqrt((dot1['x'] - dot2['x'])**2 + (dot1['y'] - dot2['y'])**2)
                if distance < self.max_distance:
                    opacity = int((1 - distance / self.max_distance) * 255)
                    color = f"#{opacity:02x}{opacity:02x}{opacity:02x}"
                    line = self.canvas.create_line(dot1['x'], dot1['y'], dot2['x'], dot2['y'],
                                                 fill=color)
                    self.lines.append(line)
        
        self.canvas.after(50, self.animate)

class URLShortenerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("URL Shortener")
        self.root.geometry("1200x750")
        self.root.configure(bg="black")
        
        self.canvas = tk.Canvas(self.root, width=1200, height=750, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.background = AnimatedBackground(self.canvas, 1200, 750)
        
        self.frame = tk.Frame(self.root, bg="#ffffff", bd=2, relief="groove")
        self.frame.place(relx=0.5, rely=0.5, anchor="center", width=500, height=400)
        
        self.label = tk.Label(self.frame, text="URL Shortener", font=("Calibri", 28, "bold"), bg="#ffffff", fg="black")
        self.label.pack(pady=15)
        
        self.url_entry = tk.Entry(self.frame, width=30, font=("Calibri", 16), bg="white", fg="black")
        self.url_entry.pack(pady=15)
        
        self.shorten_button = tk.Button(self.frame, text="Short URL", command=self.shorten, 
                                      font=("Calibri", 18, "bold"), bg="#3b82f6", fg="white",
                                      width=11, height=1)
        self.shorten_button.pack(pady=15)
        
        self.result_label = tk.Label(self.frame, text="", font=("Calibri", 16), bg="#ffffff", fg="black", wraplength=450)
        self.result_label.pack(pady=15)
        
        self.copy_button = tk.Button(self.frame, text="Copy Short URL", command=self.copy_to_clipboard, 
                                   font=("Calibri", 18, "bold"), bg="#3b82f6", fg="white",
                                   width=14, height=1)
        self.copy_button.pack_forget()
        
        self.short_url = ""

    def shorten(self):
        original_url = self.url_entry.get().strip()
        short_url, error = shorten_url(original_url)
        
        if error:
            messagebox.showerror("Error", error)
            self.result_label.config(text="")
            self.copy_button.pack_forget()
        else:
            self.short_url = short_url
            self.result_label.config(text=f"Shortened URL: {short_url}\nStats: {short_url}/stats")
            self.copy_button.pack(pady=15)

    def copy_to_clipboard(self):
        if self.short_url:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.short_url)
            messagebox.showinfo("Success", "Short URL copied to clipboard!")

class URLHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.lstrip('/')
        
        if path.endswith('/stats'):
            short_code = path[:-6]
            with sqlite3.connect(DATABASE) as conn:
                c = conn.cursor()
                c.execute('SELECT original_url, clicks FROM urls WHERE short_code = ?', (short_code,))
                result = c.fetchone()
                
                if result:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    response = f"""
                    <html>
                        <body>
                            <h1>URL Stats</h1>
                            <p>Original URL: {result[0]}</p>
                            <p>Clicks: {result[1]}</p>
                            <p>Short URL: {HOST_URL}{short_code}</p>
                        </body>
                    </html>
                    """
                    self.wfile.write(response.encode())
                else:
                    self.send_response(404)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b"URL not found")
        else:
            with sqlite3.connect(DATABASE) as conn:
                c = conn.cursor()
                c.execute('SELECT original_url, clicks FROM urls WHERE short_code = ?', (path,))
                result = c.fetchone()
                
                if result:
                    c.execute('UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?', (path,))
                    conn.commit()
                    self.send_response(302)
                    self.send_header('Location', result[0])
                    self.end_headers()
                else:
                    self.send_response(404)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b"URL not found")

def run_server():
    server_address = ('127.0.0.1', 8000)
    httpd = HTTPServer(server_address, URLHandler)
    print("Running redirect server on http://127.0.0.1:8000")
    httpd.serve_forever()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="URL Shortener with GUI")
    parser.add_argument('--url', type=str, help='URL to shorten (CLI mode)')
    args = parser.parse_args()

    if not os.path.exists(DATABASE):
        init_db()

    if args.url:
        short_url, error = shorten_url(args.url)
        if error:
            print(f"Error: {error}")
        else:
            print(f"Shortened URL: {short_url}")
        sys.exit()

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    try:
        root = tk.Tk()
        app = URLShortenerGUI(root)
        root.mainloop()
    except tk.TclError as e:
        print(f"GUI Error: {e}")
        print("Falling back to CLI mode. Please set up a display environment to use the GUI.")
        sys.exit()