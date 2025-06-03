# consulta_rag.py
import json
import faiss
import numpy as np
import requests
from sentence_transformers import SentenceTransformer

OLLAMA_API_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "mistral"

prompt_analisi = """
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

model = SentenceTransformer('all-MiniLM-L6-v2')

def recuperar_context(pregunta, top_k=5):
    index = faiss.read_index("index.faiss")
    with open("texts.json", "r", encoding="utf-8") as f:
        texts = json.load(f)["texts"]
    pregunta_embedding = model.encode([pregunta])
    dists, idxs = index.search(np.array(pregunta_embedding), top_k)
    context_relevant = [texts[i] for i in idxs[0]]
    return "\n\n".join(context_relevant)

def consulta_rag_ollama(pregunta):
    context = recuperar_context(pregunta)
    prompt = f"""{prompt_analisi}

Aquest és el context recuperat de documents administratius:

{context}

Ara, extreu les clàusules ambientals rellevants segons el format indicat:
"""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": "Ets un expert en contractació pública i sostenibilitat."},
            {"role": "user", "content": prompt}
        ]
    }
    resposta = requests.post(OLLAMA_API_URL, json=payload)
    return resposta.json()["message"]["content"]

if __name__ == "__main__":
    pregunta = "Quines obligacions ambientals s'han d'incloure durant l'execució d'un contracte?"
    print(consulta_rag_ollama(pregunta))
