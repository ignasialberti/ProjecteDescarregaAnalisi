import fitz  # PyMuPDF
import requests  # Per fer peticions HTTP a l'API local d'Ollama
import tkinter as tk
from tkinter import filedialog
import json
import os
from tqdm import tqdm
import time
from concurrent.futures import ThreadPoolExecutor
from AnalisisRAG import recuperar_context, prompt_analisi, OLLAMA_MODEL, OLLAMA_API_URL  # Assegura't que aquests estan disponibles

# Colors corporatius
color_fons = "#D6EAF8"
color_botons = "#0078D7"
color_botons_actiu = "#005A9E"

# ====================
# 0. CONFIGURACIÓ BÀSICA
# ====================

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mistral"  # o "nous-hermes", "openhermes", etc.

prompt_analisi = """

Ets un expert en contractació pública sostenible. Analitza el següent text i retorna exclusivament les clàusules ambientals rellevants en format JSON. No incloguis cap explicació, comentari, introducció o text extra.

Retorna exclusivament un llistat JSON de clàusules ambientals com aquesta:
[
  {"pagina": ..., "número de la clausula": ..., "tipus": ..., "clausula ambiental textual": "..."}
]

Si no hi ha cap clàusula ambiental rellevant, retorna exclusivament: Cap clausula ambiental rellevant.

Només això. 
"""


# ============================
# 1. DIVISIÓ EFICIENT DEL TEXT
# ============================
def dividir_text(text, max_chars=8000, overlap=1000):#mistral te un limit de context de 15000 caràcters a diferencia de nous-hermes que te 30000
    blocs = []
    i = 0
    while i < len(text):
        blocs.append(text[i:i + max_chars])
        i += max_chars - overlap
    return blocs

# =============================== 
# 2. CONSULTA A OLLAMA PER A UN BLOC
# =============================== 
def consulta_ollama_bloc(bloc, prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"{prompt}\n\n{bloc}",
        "stream": False
    }
    try:
        resposta = requests.post(OLLAMA_API_URL, json=payload)
        resposta.raise_for_status()
        resposta_json = resposta.json()
        if "response" in resposta_json:
            return resposta_json["response"]
        elif "error" in resposta_json:
            return f"[Error]: {resposta_json['error']}"
        else:
            return f"[Error]: Resposta inesperada d'Ollama: {resposta_json}"
    except Exception as e:
        return f"[Error]: {str(e)}"

# =============================== 
# 3. CONSULTA A OLLAMA PER A BLOCS
# =============================== 
def consulta_ollama_blocs(blocs):
    prompts = [prompt_analisi] + [
        """Continua l'identificació de clàusules ambientals com un expert en contractació pública sostenible seguint aquesta estructura: 
    pagina : <número de pàgina>,
    numero de la clàusula: <número de la clàusula>,
    tipus: obligacions del contractista | criteris de valoració ambiental | altres
    clausula ambinetal: <text complet de la clàusula ambiental> 
   Si no trobes clausules ambientals, No escriguis res que surti d'aquesta estructura ni cap frase introductòria o de tancament."""] * (len(blocs) - 1)
    with ThreadPoolExecutor(max_workers=4) as executor:
        resultats = executor.map(lambda args: consulta_ollama_bloc(*args), zip(blocs, prompts))
    return "\n\n".join(resultats)

# ================================ 
# 4A. FUNCIÓ PRINCIPAL PER UN SOL PDF
# ================================ 
def analitzar_fitxer_individual():
    root = tk.Tk()
    root.withdraw()
    ruta = filedialog.askopenfilename(title="Selecciona un fitxer PDF", filetypes=[("PDF files", "*.pdf")])

    if not ruta:
        print(" No s'ha seleccionat cap fitxer.")
        return

    print(f"\n Fitxer seleccionat: {ruta}")
    text = ""

    try:
        with fitz.open(ruta) as doc:
            for pagina in tqdm(doc, desc="Llegint pàgines"):
                text += pagina.get_text()

        if not text.strip():
            print(" El fitxer no conté text llegible.")
            return

        blocs = [text] if len(text) < 8001 else dividir_text(text)

        print(f"\n Nombre de blocs: {len(blocs)}")
        resposta = consulta_ollama_blocs(blocs)

        if resposta:
            print("\n Resposta del model local (Ollama):")
            print("=" * 60)
            print(resposta)
            print("=" * 60)

            output_path = ruta.replace(".pdf", "_analisi.txt")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(resposta)
            print(f"\n Resposta guardada a: {output_path}")
        else:
            print(" No s'ha rebut cap resposta.")

    except Exception as e:
        print(" Error obrint el PDF:", str(e))

# ================================================================== 
# 4B. FUNCIÓ PER ANALITZAR AUTOMÀTICAMENT UNA CARPETA
# ================================================================== 
def analitzar_documents_carpeta():
    base_dir = "Documents_Descarregats_Playwright"

    if not os.path.isdir(base_dir):
        print(f" No s'ha trobat la carpeta '{base_dir}'.")
        return

    for root_dir, subdirs, files in os.walk(base_dir):
        for fitxer in files:
            if fitxer.lower().endswith(".pdf"):
                pdf_path = os.path.join(root_dir, fitxer)
                print(f"\n📄 Processant PDF: {pdf_path}")
                text = ""

                try:
                    with fitz.open(pdf_path) as doc:
                        for pagina in tqdm(doc, desc="Llegint pàgines", leave=False):
                            text += pagina.get_text()
                except Exception as e:
                    print(f" Error obrint el PDF {pdf_path}: {str(e)}")
                    continue

                if not text.strip():
                    print(f" El fitxer {pdf_path} no conté text llegible.")
                    continue

                blocs = [text] if len(text) < 25000 else dividir_text(text)
                print(f" Nombre de blocs: {len(blocs)}")

                resposta = consulta_ollama_blocs(blocs)

                if resposta:
                    output_path = pdf_path.replace(".pdf", "_analisi.txt")
                    try:
                        with open(output_path, "w", encoding="utf-8") as f:
                            f.write(resposta)
                        print(f" Anàlisi desada a: {output_path}")
                    except Exception as e:
                        print(f" Error desant l'arxiu de sortida: {e}")
                else:
                    print(" No s'ha rebut cap resposta del model local.")

# ========================= 
# 5. INTERFÍCIE GRÀFICA
# ========================= 
def tria_opcio():
    seleccio = {"valor": None}

    def analisi_individual():
        seleccio["valor"] = "individual"
        root.destroy()

    def analisi_carpeta():
        seleccio["valor"] = "carpeta"
        root.destroy()

    root = tk.Tk()
    root.title("Selecció d'anàlisi")
    root.configure(bg=color_fons)
    root.resizable(False, False)
    root.geometry("420x220")

    label = tk.Label(
        root, text="Quina anàlisi vols fer?", bg=color_fons,
        font=("Helvetica", 13, "bold")
    )
    label.pack(padx=30, pady=(24, 12), fill="x")

    btn1 = tk.Button(
        root, text="Analitzar un fitxer individual", command=analisi_individual,
        bg=color_botons, fg="white", font=("Helvetica", 12, "bold"),
        activebackground=color_botons_actiu, width=30, pady=8, relief="flat"
    )
    btn1.pack(padx=30, pady=8, fill="x")

    btn2 = tk.Button(
        root, text="Analitzar tots els documents de la carpeta", command=analisi_carpeta,
        bg=color_botons, fg="white", font=("Helvetica", 12, "bold"),
        activebackground=color_botons_actiu, width=30, pady=8, relief="flat"
    )
    btn2.pack(padx=30, pady=(0, 24), fill="x")

    root.mainloop()
    return seleccio["valor"]

def executar_analisi():
    opcio = tria_opcio()
    if opcio == "individual":
        analitzar_fitxer_individual()
    elif opcio == "carpeta":
        analitzar_documents_carpeta()

# ========================= 
# 6. EXECUCIÓ D'EXEMPLE
# ========================= 
if __name__ == "__main__":
    executar_analisi()

def analitza_document_amb_rag(text_document):
    context_base = recuperar_context("clàusules ambientals en contractació pública", top_k=5)
    prompt = f"""{prompt_analisi}

Coneixement base:
{context_base}

Document a analitzar:
{text_document}

Ara, extreu les clàusules ambientals rellevants segons el format indicat:
"""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    resposta = requests.post(OLLAMA_API_URL, json=payload)
    resposta_json = resposta.json()
    if "response" in resposta_json:
        return resposta_json["response"]
    elif "error" in resposta_json:
        raise RuntimeError(f"Error de l'API Ollama: {resposta_json['error']}")
    else:
        raise RuntimeError(f"Resposta inesperada d'Ollama: {resposta_json}")
