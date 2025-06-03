# generar_index.py
import os
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import tkinter as tk
from tkinter import filedialog

def generar_index(max_len=500):
    # Selecció de carpeta amb Tkinter
    root = tk.Tk()
    root.withdraw()
    carpeta = filedialog.askdirectory(title="Selecciona la carpeta amb els TXT per indexar")
    root.destroy()
    if not carpeta:
        print("No s'ha seleccionat cap carpeta.")
        return

    model = SentenceTransformer('all-MiniLM-L6-v2')
    documents = []
    metadades = []

    for root_dir, _, fitxers in os.walk(carpeta):
        for fitxer in fitxers:
            if fitxer.endswith(".txt"):
                with open(os.path.join(root_dir, fitxer), "r", encoding="utf-8") as f:
                    text = f.read()
                    parts = [text[i:i+max_len] for i in range(0, len(text), max_len)]
                    documents.extend(parts)
                    metadades.extend([{"fitxer": fitxer, "index": i} for i in range(len(parts))])

    if not documents:
        print("No s'han trobat fitxers TXT amb contingut a la carpeta seleccionada.")
        return

    embeddings = model.encode(documents, show_progress_bar=True)
    embeddings = np.array(embeddings)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    faiss.write_index(index, "index.faiss")
    with open("texts.json", "w", encoding="utf-8") as f:
        json.dump({"texts": documents, "metadades": metadades}, f)

    print(f"✅ Index generat amb {len(documents)} fragments.")

if __name__ == "__main__":
    generar_index()
