# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk  # Per utilitzar estils moderns
import threading
import subprocess
import os
import sys
import tkinter.scrolledtext as scrolledtext

# Importem els mòduls dels scripts (pressuposem que es troben al mateix directori)
try:
    import AnalisisDeepseek
except ImportError:
    AnalisisDeepseek = None

try:
    import AnalisisLocalOllama
except ImportError:
    AnalisisLocalOllama = None

try:
    import DescarregaPlaywright
except ImportError:
    DescarregaPlaywright = None

try:
    import DescarregaSelenium
except ImportError:
    DescarregaSelenium = None

# Referències globals als processos de descàrrega
proc_desc_playwright = None
proc_desc_selenium = None

# Variables globals per als fils d'anàlisi automàtica
thread_deepseek = None
thread_ollama = None

def run_analisis_deepseek():
    global thread_deepseek
    if AnalisisDeepseek is None:
        messagebox.showerror("Error", "No s'ha pogut importar AnalisisDeepseek.py")
        return
    # Ja no preguntem, només cridem la funció principal
    thread_deepseek = threading.Thread(target=AnalisisDeepseek.executar_analisi, daemon=True)
    thread_deepseek.start()

def stop_analisi_deepseek():
    global thread_deepseek
    # Aquí pots implementar un flag d'aturada si vols aturar el fil de veritat
    messagebox.showinfo("Aturat", "Procés d'anàlisi Deepseek aturat (implementa la lògica d'aturada real si cal).")

def run_analisis_local_ollama():
    global thread_ollama
    if AnalisisLocalOllama is None:
        messagebox.showerror("Error", "No s'ha pogut importar AnalisisLocalOllama.py")
        return
    # Ja no preguntem, només cridem la funció principal
    thread_ollama = threading.Thread(target=AnalisisLocalOllama.executar_analisi, daemon=True)
    thread_ollama.start()

def stop_analisi_ollama():
    global thread_ollama
    # Aquí pots implementar un flag d'aturada si vols aturar el fil de veritat
    messagebox.showinfo("Aturat", "Procés d'anàlisi Ollama aturat (implementa la lògica d'aturada real si cal).")

def run_descarrega_playwright():
    global proc_desc_playwright
    try:
        script_path = os.path.join(os.path.dirname(__file__), "DescarregaPlaywright.py")
        proc_desc_playwright = subprocess.Popen(
            ["python", script_path]
            # Ja no cal redirigir stdout ni crear cap fil per llegir la sortida
        )
    except Exception as e:
        messagebox.showerror("Error", f"No s'ha pogut executar DescarregaPlaywright.py:\n{e}")

def stop_descarrega_playwright():
    global proc_desc_playwright
    if proc_desc_playwright and proc_desc_playwright.poll() is None:
        proc_desc_playwright.terminate()
        messagebox.showinfo("Aturat", "Descàrrega Playwright aturada.")
    else:
        messagebox.showinfo("Info", "No hi ha cap descàrrega Playwright activa.")

def run_descarrega_selenium():
    global proc_desc_selenium
    try:
        script_path = os.path.join(os.path.dirname(__file__), "DescarregaSelenium.py")
        proc_desc_selenium = subprocess.Popen(
            ["python", script_path]
        )
    except Exception as e:
        messagebox.showerror("Error", f"No s'ha pogut executar DescarregaSelenium.py:\n{e}")

def stop_descarrega_selenium():
    global proc_desc_selenium
    if proc_desc_selenium and proc_desc_selenium.poll() is None:
        proc_desc_selenium.terminate()
        messagebox.showinfo("Aturat", "Descàrrega Selenium aturada.")
    else:
        messagebox.showinfo("Info", "No hi ha cap descàrrega Selenium activa.")

# Afegiu aquest codi a la part on definiu la GUI principal (on hi ha les altres pestanyes)
def executar_analisi_local_rag():
    ruta = os.path.join(os.path.dirname(__file__), "RAG", "AnalisisRAGLocalOllama.py")
    subprocess.Popen([sys.executable, ruta])

def executar_creacio_embeddings():
    ruta = os.path.join(os.path.dirname(__file__), "RAG", "embeddings.py")
    subprocess.Popen([sys.executable, ruta])

# Creació de la finestra principal de l'aplicació
root = tk.Tk()
root.title("Aplicació d'Anàlisi")
root.resizable(False, False)

# Configuració del color de fons de la interfície
root.configure(bg="#D6EAF8")  # Blau clar com a color de fons

# Configuració d'estil amb ttk.Style
style = ttk.Style()
style.theme_use("clam")

# Colors personalitzats
color_fons = "#D6EAF8"      # Blau clar per al fons general i pestanyes
color_botons = "#0078D7"    # Blau fort per als botons
color_botons_actiu = "#005A9E"

# Estil per als botons
style.configure("TButton", background=color_botons, foreground="white", font=("Helvetica", 12, "bold"), padding=10)
style.map("TButton", background=[("active", color_botons_actiu)])

# Estil per a les pestanyes del notebook
style.configure("TNotebook", background=color_fons, borderwidth=0)
style.configure("TNotebook.Tab", background=color_fons, foreground="#154360", font=("Helvetica", 11, "bold"), padding=[10, 5])
style.map("TNotebook.Tab",
          background=[("selected", "#85C1E9")],   # Blau una mica més intens per la pestanya seleccionada
          foreground=[("selected", "#154360")])

# Amplada fixa per als botons
button_width = 120

# Creació del notebook per a pestanyes
notebook = ttk.Notebook(root, style="TNotebook")
notebook.pack(padx=10, pady=10, expand=True, fill="both")

# Pestanya DESCÀRREGA
frame_desc = tk.Frame(notebook, bg=color_fons)

# Paràmetres d'estil
button_height = 3  # Alçada en "text lines" per als botons
button_width = 30  # Amplada per als botons blaus
stop_width = 5     # Amplada per als botons STOP

for idx, (text, run_cmd, stop_cmd) in enumerate([
    ("Descarrega Playwright", run_descarrega_playwright, stop_descarrega_playwright),
    ("Descarrega Selenium", run_descarrega_selenium, stop_descarrega_selenium)
]):
    row = tk.Frame(frame_desc, bg=color_fons)
    # Botó blau (ttk no permet height, així que usem tk.Button per igualar-ho tot)
    btn = tk.Button(
        row, text=text, command=run_cmd,
        bg=color_botons, fg="white", font=("Helvetica", 12, "bold"),
        width=button_width, height=button_height, relief="flat", activebackground=color_botons_actiu
    )
    btn_stop = tk.Button(
        row, text="STOP", command=lambda: None,  # Substitueix per la funció d'aturada si en tens
        bg="#E74C3C", fg="white", font=("Helvetica", 12, "bold"),
        width=stop_width, height=button_height, relief="flat", activebackground="#922B21"
    )
    btn.grid(row=0, column=0, padx=(0, 5), pady=10, sticky="nsew")
    btn_stop.grid(row=0, column=1, padx=(5, 0), pady=10, sticky="nsew")
    row.grid_columnconfigure(0, weight=1)
    row.grid_columnconfigure(1, weight=0)
    row.pack(fill="x", padx=10, pady=5)

notebook.add(frame_desc, text="Descàrrega")

# Pestanya ANÀLISI
frame_ana = tk.Frame(notebook, bg=color_fons)

for idx, (text, run_cmd, stop_cmd) in enumerate([
    ("Anàlisi Deepseek", run_analisis_deepseek, stop_analisi_deepseek),
    ("Anàlisi Ollama (local)", run_analisis_local_ollama, stop_analisi_ollama)
]):
    row = tk.Frame(frame_ana, bg=color_fons)
    btn = tk.Button(
        row, text=text, command=run_cmd,
        bg=color_botons, fg="white", font=("Helvetica", 12, "bold"),
        width=button_width, height=button_height, relief="flat", activebackground=color_botons_actiu
    )
    btn_stop = tk.Button(
        row, text="STOP", command=lambda: None,  # Substitueix per la funció d'aturada si en tens
        bg="#E74C3C", fg="white", font=("Helvetica", 12, "bold"),
        width=stop_width, height=button_height, relief="flat", activebackground="#922B21"
    )
    btn.grid(row=0, column=0, padx=(0, 5), pady=10, sticky="nsew")
    btn_stop.grid(row=0, column=1, padx=(5, 0), pady=10, sticky="nsew")
    row.grid_columnconfigure(0, weight=1)
    row.grid_columnconfigure(1, weight=0)
    row.pack(fill="x", padx=10, pady=5)

notebook.add(frame_ana, text="Anàlisi")

# Pestanya RAG LOCAL
frame_rag = tk.Frame(notebook, bg=color_fons)

for idx, (text, run_cmd, stop_cmd) in enumerate([
    ("Anàlisi Local amb RAG", executar_analisi_local_rag, lambda: None),  # Substitueix lambda si tens stop real
    ("Creació de embeddings", executar_creacio_embeddings, lambda: None)
]):
    row = tk.Frame(frame_rag, bg=color_fons)
    btn = tk.Button(
        row, text=text, command=run_cmd,
        bg=color_botons, fg="white", font=("Helvetica", 12, "bold"),
        width=button_width, height=button_height, relief="flat", activebackground=color_botons_actiu
    )
    btn_stop = tk.Button(
        row, text="STOP", command=stop_cmd,
        bg="#E74C3C", fg="white", font=("Helvetica", 12, "bold"),
        width=stop_width, height=button_height, relief="flat", activebackground="#922B21"
    )
    btn.grid(row=0, column=0, padx=(0, 5), pady=10, sticky="nsew")
    btn_stop.grid(row=0, column=1, padx=(5, 0), pady=10, sticky="nsew")
    row.grid_columnconfigure(0, weight=1)
    row.grid_columnconfigure(1, weight=0)
    row.pack(fill="x", padx=10, pady=5)

notebook.add(frame_rag, text="RAG Local")

# Inici del bucle principal de Tkinter
root.mainloop()
