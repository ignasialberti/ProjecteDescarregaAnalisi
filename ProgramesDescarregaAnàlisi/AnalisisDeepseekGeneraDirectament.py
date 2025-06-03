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
Et proporcionaré diversos fitxers en format PDF que contenen documents contractuals. Necessito que els analitzis com si fossis un expert en ambientalització de la contractació pública i avaluïs fins a quin punt incorporen criteris ambientals.

1. Objectiu de l’anàlisi:
Has d’identificar i destacar qualsevol requisit relacionat amb la sostenibilitat ambiental, nomès si es AMBIENTAL cal que ho treballis. Analitza amb detall els següents elements:

- Clàusules ambientals explícites (ex: gestió de residus, ús de materials sostenibles, control d’emissions)
- Referències a normatives ambientals (locals, estatals, europees, internacionals)
- Exigències sobre distintius ecològics o certificacions ambientals (ex. EMAS, ISO 14001, ecoetiquetes)
- Límits d’emissions, requisits d’eficiència energètica o impacte ambiental
- Compromisos de sostenibilitat ambiental(en l’execució, materials, subministraments o gestió de residus)
- Mencions a la contractació sostenible desde un punt de vista ambiental(com puntuació addicional o criteris d’adjudicació ambientals)
- La sostenibilitat ambiental no inclou aspectes socials o laborals, només medi ambient. (ex: no incloguis accesibilitat, innovació ,inclusivitat, igualtat, conciliació, persones amb discapacitat, etc.)

2. Com estructurar la resposta:
Per a cada document:
- Indica si s’hi troben clàusules ambientals o no.
- No m'expliquis el contingut del document, només les referències ambientals.
- Si no n’hi ha, indica-ho clarament al final: *“No s’han trobat referències ambientals”, al cos del text no cal posar-ho*.
- Si n’hi ha, resumeix les clàusules trobades de manera concisa, especificant:
   - On apareixen (número de pàgina i clàusula si és possible)
   - Tipus de menció: obligació contractual, criteri d’adjudicació, recomanació no vinculant, o clàusula estàndard
   - Inclou textualment els fragments on es parla de sostenibilitat, medi ambient, residus, o qualsevol concepte relacionat

3. Precisió addicional:
- Llegeix tot el document, inclosos annexos i condicions tècniques.
- Inclou també referències genèriques com “gestió ambiental correcta” encara que siguin clàusules habituals.
-Si són clàusules genèriques o poc efectives (ex: frases buides o poc concretes), no fa falta que les incloguis.
- Si hi ha mencions a la sostenibilitat però no són ambientals, ignora-ho clarament.
- Obvia  mencións  poc rellevants o genèriques: si existeix, Cenrat en clausueles o apartats que aportin informació ambiental concreta i rellevant.

4. Format de la resposta:
- Escriu de forma clara i estructurada. Fes servir llistes si cal.
-No cal que mencionis aspectes del document que no tenen res a veure amb la gestió ambiental o la sostenbilitat del medi ambient.
- Sigues explícit i cita textualment fragments com: *“Fer una correcta gestió ambiental del seu servei…”*
- Quan no hi hagi mencions ambientals, ignora-ho clarament.
- Evita repeticions i sigues concís. No cal repetir el mateix en cada document.
-Indica finalment entre quines pagines s'ha fet l'analisis i entre quins apartats o clàusules. (principi-final)
-No facis conclusions generals sobre el document, només menciona les referències o clausules ambientals, ja que desprès d'un bloc d'anàlisi hi ha un altre bloc de text que es processarà amb el mateix prompt i que pot contenir més informació ambiental.
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
    prompts = [prompt] + ["Continua l'anàlisi del document anterior amb aquest nou fragment.Centra't només en NOVES mencions ambientals rellevants. Ignora el contingut que no aporti informació ambiental nova. Si no hi ha cap menció ambiental, respon exclusivament: 'Cap menció ambiental rellevant en aquest fragment'. "] * (len(blocs) - 1) #AIXO HO HEM CANVIAT PER MILLORAR LA COHESIO DELS FRAGMENTS DE LA RESPOSTA
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
    cercant tots els PDFs i aplicant el procés d'anàlisi. Guarda només les
    clàusules ambientals rellevants en format CSV i XLSX sense símbols * ni #.
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
                    continue

                # Dividir en blocs i enviar a l'API
                blocs = [text] if len(text) < 25000 else dividir_text(text, max_chars=25000)
                resposta = consulta_deepseek_blocs(blocs)

                if resposta:
                    # Processa la resposta per extreure clàusules ambientals netes
                    codi_exp = os.path.splitext(os.path.basename(pdf_path))[0]
                    clausules = parse_clauses_net(resposta, codi_exp)
                    totes_les_clausules.extend(clausules)

    if totes_les_clausules:
        df = pd.DataFrame(totes_les_clausules)
        output_csv = os.path.join(base_dir, "clausules_ambientals_net.csv")
        output_xlsx = os.path.join(base_dir, "clausules_ambientals_net.xlsx")
        df.to_csv(output_csv, index=False, encoding="utf-8-sig")
        df.to_excel(output_xlsx, index=False)
        print(f"\n✅ Fitxer CSV generat: {output_csv}")
        print(f"✅ Fitxer Excel generat: {output_xlsx}")
    else:
        print("\nℹ️ No s'han trobat clàusules ambientals a cap document.")


def parse_clauses_net(response_text, codi_exp):
    """
    Extreu clàusules ambientals rellevants i elimina símbols com # i *.
    Prioritza la classificació pel nom del fitxer (codi_exp).
    """
    entries = []
    paraules_clau = [
        "gestió ambiental", "residus", "emissions", "embalatges", "sostenibilitat",
        "ecoetiqueta", "eficiència energètica", "impacte ambiental", "certificació ambiental",
        "ISO 14001", "EMAS", "normativa ambiental", "cura del medi ambient",
        "contractació pública sostenible"
    ]

    tipus_map = {
        "PCAP": ["pcap", "plec administratiu", "pliego administrativo"],
        "PPT": ["ppt", "plec tècnic", "pliego técnico"]
    }

    fragments = response_text.split("\n\n")
    codi_exp_lower = codi_exp.lower()

    for fragment in fragments:
        fragment_lower = fragment.lower()

        if any(kw in fragment_lower for kw in paraules_clau):
            # Elimina símbols i neteja
            clausula_neta = re.sub(r'[#*]', '', fragment.strip().replace("\n", " ")).strip()
            if not clausula_neta:
                continue

            # Prioritat 1: deduir pel codi del fitxer
            if "pcap" in codi_exp_lower:
                tipus_final = "PCAP"
            elif "ppt" in codi_exp_lower:
                tipus_final = "PPT"
            else:
                # Prioritat 2: deduir pel text de la clàusula
                tipus_final = "ALTRES"
                for tipus, mots in tipus_map.items():
                    if any(m in fragment_lower for m in mots):
                        tipus_final = tipus
                        break

            entries.append({
                "CODI EXP": codi_exp,
                "PCAP/PPT": tipus_final,
                "CLAUSULA": clausula_neta
            })

    return entries

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

def parse_clauses(response_text, codi_exp):
    """
    Extreu clàusules ambientals encara que no segueixin un patró estricte de format.
    Busca paraules clau ambientals i intenta classificar el tipus de document (PCAP/PPT).
    """
    entries = []
    paraules_clau = [
        "gestió ambiental", "residus", "emissions", "embalatges", "sostenibilitat",
        "ecoetiqueta", "eficiència energètica", "impacte ambiental", "certificació ambiental",
        "ISO 14001", "EMAS", "normativa ambiental", "cura del medi ambient", "contractació pública sostenible"
    ]

    tipus_map = {
        "PCAP": ["pcap", "plec administratiu", "pliego administrativo"],
        "PPT": ["ppt", "plec tècnic", "pliego técnico"]
    }

    fragments = response_text.split("\n\n")
    for fragment in fragments:
        fragment_lower = fragment.lower()

        if any(kw in fragment_lower for kw in paraules_clau):
            tipus_final = "ALTRES"
            for tipus, mots in tipus_map.items():
                if any(m in fragment_lower for m in mots):
                    tipus_final = tipus
                    break

            entries.append({
                "CODI EXP": codi_exp,
                "PCAP/PPT": tipus_final,
                "CLAUSULA": fragment.strip().replace("\n", " ")
            })

    return entries

if __name__ == "__main__":
    executar_analisi()
