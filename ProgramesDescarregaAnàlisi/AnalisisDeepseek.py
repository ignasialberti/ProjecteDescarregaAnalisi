import fitz # PyMuPDF # Per llegir PDFs
import requests # Per fer peticions HTTP a l'API   
import tkinter as tk # Per la GUI de selecció de fitxers  per a l'usuari 
from tkinter import filedialog # Per la GUI de selecció de fitxers 
import json # Per gestionar JSONs, els JSONs són el format de les respostes de l'API
import os # Per gestionar rutes de fitxers i directoris, les carpetes i subcarpetes
from tqdm import tqdm #Aquest modul és per mostrar una barra de progrés a la terminal, per veure el progrés de la lectura del PDF
import time # Per gestionar el temps d'espera entre peticions a l'API, per evitar bloquejos per massa peticions
from concurrent.futures import ThreadPoolExecutor # Per executar múltiples fils de manera eficient, per enviar les peticions a l'API en paral·lel
import re # Per les expressions regulars, útils per analitzar el text
import pandas as pd
import unicodedata
#ULTIMA ACTUALTZACIÓ: 2025-06-02
# Colors corporatius per la GUI
color_fons = "#D6EAF8"      # Blau clar per al fons general i pestanyes
color_botons = "#0078D7"    # Blau fort per als botons
color_botons_actiu = "#005A9E"

# ====================
# 0.CONFIGURACIÓ BÀSICA CANVIO EL PROMPT D'AQUESTA FUNCIó
# ====================

DEEPSEEK_API_KEY = "sk-6de891359c904e3e9d282505450fcb62" 
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

prompt = """
Ets un expert en contractació pública sostenible. Analitza el següent text i retorna exclusivament les clàusules ambientals rellevants en format JSON. No incloguis cap explicació, comentari, introducció o text extra.

Format exacte:

[
  {
    "pagina": <número de pàgina>,
    "número de la clausula": <número de la clàusula>,
    "tipus": "obligacions del contractista" | "criteris de valoració ambiental" | "altres",
    "clausula": "<text complet de la clàusula>"
  }
]

Si no hi ha cap clàusula ambiental rellevant, retorna exclusivament: Cap clausula ambiental rellevant.

Només el JSON. No escriguis cap frase abans ni després.
"""

# ============================
# 1.DIVISIÓ EFICIENT DEL TEXT
# ============================
#En aquesta funcio es divideix el 7text en blocs de 5000 caràcters per evitar errors de longitud a l'API.
# Aquesta funció es pot modificar per ajustar la longitud dels blocs segons les necessitats de l'usuari.
def dividir_text(text, max_chars=50000, overlap=2000):
    blocs = []
    i = 0
    while i < len(text):
        blocs.append(text[i:i + max_chars])
        i += max_chars - overlap
    return blocs

# ==============================
# 2.FUNCIONS D'ANÀLISI EN PARAL.LEL
# ==============================
## Aquesta funció consulta DeepSeek per cada bloc de text, enviant el prompt d'anàlisi i el bloc corresponent.
## Utilitza un executor de fils per enviar les peticions en paral·lel, millorant l'eficiència del procés.
def consulta_deepseek_bloc(bloc, prompt):
    #Definim un diccionari payload que serà el contingut de la petició http a l'API de DeepSeek.
    # El diccionari conté el model a utilitzar, els missatges (incloent el prompt i el bloc de text) i el màxim de tokens a retornar.
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "Ets un expert en contractació pública i sostenibilitat."},
            {"role": "user", "content": f"{prompt}\n\n{bloc}"}
        ],
        "max_tokens": 3500 #Longitud de la  resposta màxima en tokens. 3072 abans
    }
    # Definim els headers de la petició, incloent la clau d'autorització i el tipus de contingut.
    # La clau d'autorització és necessària per autenticar-nos amb l'API de DeepSeek.
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    # Fem la petició POST a l'API de DeepSeek, enviant els headers i el payload.
    # Si la petició és exitosa, retornem el contingut de la resposta.
    try:
        resposta = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload)
        resposta.raise_for_status()
        return resposta.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[Error]: {str(e)}"
# ================================
# 3.FUNCIONS D'ANÀLISI EN PARALEL
# ================================
# Aquesta funció consulta DeepSeek per cada bloc de text, enviant el prompt d'anàlisi i el bloc corresponent.
# Utilitza un executor de fils per enviar les peticions en paral·lel, millorant l'eficiència del procés.
#"Continua l'anàlisi del document anterior amb aquest nou fragment. Resumeix només allò nou i evita repetir el que ja s’ha dit."
# Aquesta funció recorre tots els blocs i els envia a l'API, esperant les respostes de manera eficient.
def consulta_deepseek_blocs(blocs):
        prompts = [prompt] + [
            """Continua l'identificació de clàusules ambientals com un expert en contractació pública sostenible seguint aquesta estructura: 
    pagina : <número de pàgina>,
    numero de la clàusula: <número de la clàusula>,
    tipus: obligacions del contractista | criteris de valoració ambiental | altres
    clausula ambinetal: <text complet de la clàusula ambiental> 
   Si no trobes clausules ambientals, No escriguis res que surti d'aquesta estructura ni cap frase introductòria o de tancament."""
        ] * (len(blocs) - 1) #AIXO HO HEM CANVIAT PER MILLORAR LA COHESIO DELS FRAGMENTS DE LA RESPOSTA
        with ThreadPoolExecutor(max_workers=4) as executor:
            resultats = executor.map(lambda args: consulta_deepseek_bloc(*args), zip(blocs, prompts))
        return "\n\n".join(resultats)

# ================================
# 4A.FUNCIÓ PRINCIPAL PER UN SOL PDF
# ================================
#
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

        if len(text) < 25000:
            blocs = [text]
        else:
            blocs = dividir_text(text, max_chars=25000)

        print(f"\n Nombre de blocs: {len(blocs)}")
        resposta = consulta_deepseek_blocs(blocs)

        if resposta:
            print("\n Resposta de DeepSeek:")
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
# 4B.NOVA FUNCIÓ: ANALITZAR AUTOMÀTICAMENT UNA CARPETA I LES SUBCARPETES
# ==================================================================

def analitzar_documents_carpeta():
    """
    Permet seleccionar la carpeta a analitzar i recorre totes les subcarpetes,
    cercant tots els PDFs i aplicant el procés d'anàlisi.
    """
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    base_dir = filedialog.askdirectory(title="Selecciona la carpeta amb els PDFs a analitzar")
    root.destroy()

    if not base_dir:
        print(" No s'ha seleccionat cap carpeta.")
        return

    totes_les_clausules = []

    for root_dir, subdirs, files in os.walk(base_dir):
        for fitxer in files:
            if fitxer.lower().endswith(".pdf"):
                pdf_path = os.path.join(root_dir, fitxer)
                print(f"\n📄 Processant PDF: {pdf_path}")
                text = ""

                # Extreure text del PDF
                try:
                    with fitz.open(pdf_path) as doc:
                        for pagina in tqdm(doc, desc="Llegint pàgines", leave=False):
                            text += pagina.get_text()
                except Exception as e:
                    print(f" Error obrint el PDF {pdf_path}: {str(e)}")
                    continue

                if not text.strip():
                    print(f" El fitxer {pdf_path} no conté text llegible.")
                    output_path = pdf_path.replace(".pdf", "_analisi.txt")
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write("No hi ha text seleccionable, text escanejat")
                    print(f" Missatge desat a: {output_path}")
                    continue

                # Dividir en blocs i enviar a l'API
                blocs = [text] if len(text) < 25000 else dividir_text(text, max_chars=25000)
                resposta = consulta_deepseek_blocs(blocs)

                if resposta:
                    # Desa un .txt per a cada PDF
                    output_path = pdf_path.replace(".pdf", "_analisi.txt")
                    try:
                        with open(output_path, "w", encoding="utf-8") as f:
                            f.write(resposta)
                        print(f" Anàlisi desada a: {output_path}")
                    except Exception as e:
                        print(f" Error desant l'arxiu de sortida: {e}")

                    # Nom del fitxer sense extensió = CODI EXP
                    codi_exp = os.path.splitext(os.path.basename(pdf_path))[0]
                    clausules = parse_clauses_from_text_dedup (resposta, codi_exp)
                    totes_les_clausules.extend(clausules)

    if totes_les_clausules:
        df = pd.DataFrame(totes_les_clausules)
        output_excel = os.path.join(base_dir, "clausules_ambientals.xlsx")
        df.to_excel(output_excel, index=False)
        print(f"\n✅ Fitxer Excel generat: {output_excel}")
    else:
        print("\nℹ️ No s'han trobat clàusules ambientals a cap document.")


# =========================
# 6.EXECUCIÓ D'EXEMPLE ----> Triar una de les dues opcions
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
    root.geometry("420x220")  # Amplia la finestra

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

def normalitzar_clausula(text):
    text = text.lower().strip()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return re.sub(r'\s+', ' ', text)

def eliminar_duplicats(resultats):
    vistes = set()
    finals = []
    for item in resultats:
        clau = normalitzar_clausula(item['CLAUSULA'])
        if clau not in vistes:
            vistes.add(clau)
            finals.append(item)
    return finals

def parse_clauses_from_text_dedup(response_text, codi_exp):
    pattern = re.compile(
        r"p[aà]gina\s*[:\.]?\s*(\d+)[,]*\s*[\n\r]+"
        r"numero de la cl[aà]usula\s*[:\.]?\s*([^\n\r,]+)[,]*\s*[\n\r]+"
        r"tipus\s*[:\.]?\s*(obligacions del contractista|criteris de valoració ambiental|altres)[,]*\s*[\n\r]+"
        r"cl[aà]usula ambiental\s*[:\.]?\s*(?:\*?\"?)(.*?)(?:\"?\*?)(?=\n{2,}|\r{2,}|$)",
        re.IGNORECASE | re.DOTALL
    )

    pattern_alt = re.compile(
        r"p[aà]gina\s*[:\.]?\s*(\d+)[,]*\s*[\n\r]+"
        r"numero de la cl[aà]usula\s*[:\.]?\s*([^\n\r,]+)[,]*\s*[\n\r]+"
        r"tipus\s*[:\.]?\s*(obligacions del contractista|criteris de valoració ambiental|altres)[,]*\s*[\n\r]+"
        r"cl[aà]usula\s*[:\.]?\s*(?:\*?\"?)(.*?)(?:\"?\*?)(?=\n{2,}|\r{2,}|$)",
        re.IGNORECASE | re.DOTALL
    )

    resultats = []
    nom_lower = os.path.basename(codi_exp).lower()
    tipus_fitxer = "PCAP" if "pcap" in nom_lower else "PPT" if "ppt" in nom_lower else "NoDefinit"

    # Cerca amb els dos patrons
    for match in list(pattern.finditer(response_text)) + list(pattern_alt.finditer(response_text)):
        pagina, num_clausula, tipus, clausula = match.groups()
        clausula = re.sub(r"\s+", " ", clausula).strip()
        resultats.append({
            "CODI EXPEDIENT": codi_exp,
            "PCAP/PPT": tipus_fitxer,
            "PÀGINA": pagina,
            "NÚM. CLAUSULA": num_clausula,
            "TIPUS": tipus,
            "CLAUSULA": clausula
        })

    resultats = eliminar_duplicats(resultats)

    if not resultats:
        resultats.append({
            "CODI EXPEDIENT": codi_exp,
            "PCAP/PPT": tipus_fitxer,
            "PÀGINA": "-",
            "NÚM. CLAUSULA": "-",
            "TIPUS": "cap clausula ambiental",
            "CLAUSULA": "No s’han identificat clàusules ambientals en aquest document."
        })

    return resultats

if __name__ == "__main__":
    executar_analisi()
