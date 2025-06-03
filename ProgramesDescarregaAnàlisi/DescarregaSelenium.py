import pandas as pd
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import time
import os
import requests

PDF_KEYWORDS = [
    "pcap", "pcp", "ppt-", "prescripcions tecniques", "prescripcions tècniques",
    "pca", "plec clàusules", "clausulesadministratives", "plec", "pct", "ppt",
    "pliego administrativo", "pliego tecnico", "plec administratiu", "plec tècnic",
    "tècnic", "plec condicions", "normes reguladores"
]

def is_relevant_pdf(text):
    txt = text.lower()
    return any(k in txt for k in PDF_KEYWORDS)

def sanitize_folder_name(folder_name):
    invalid_chars = r'\/:*?"<>|'
    for char in invalid_chars:
        folder_name = folder_name.replace(char, '_')
    return folder_name

def descarregar_documents():
    archivo_excel = "Contractes 2024_només amb publicitat.xlsx"
    hoja_datos = pd.read_excel(archivo_excel)

    if 'CODI_EXPEDIENT' in hoja_datos.columns and 'ENLLAC_PUBLICACIO' in hoja_datos.columns:
        codis_expedient = hoja_datos['CODI_EXPEDIENT']
        enllacos = hoja_datos['ENLLAC_PUBLICACIO']

        for codi_expedient, enllac in zip(codis_expedient, enllacos):
            nom_carpeta = sanitize_folder_name(str(codi_expedient))
            carpeta_descargas = os.path.join("Documents_Descarregats_Ajuntament", nom_carpeta)
            if not os.path.exists(carpeta_descargas):
                os.makedirs(carpeta_descargas)

            from selenium.webdriver.chrome.options import Options
            options = Options()
            prefs = {
                "download.default_directory": os.path.abspath(carpeta_descargas),
                "download.prompt_for_download": False,
                "plugins.always_open_pdf_externally": True
            }
            options.add_experimental_option("prefs", prefs)

            driver = webdriver.Chrome(options=options)

            try:
                driver.get(enllac)

                try:
                    accept_cookies_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Accepta')]"))
                    )
                    accept_cookies_button.click()
                except Exception:
                    print("No s'ha trobat el botó de cookies. Continuant...")

                # Intentar clicar "Anunci de licitació", després "Anuncio de licitación", després "Adjudicació"
                try:
                    Anunci_link = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.LINK_TEXT, "Anunci de licitació"))
                    )
                    Anunci_link.click()
                    time.sleep(3)
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
                    time.sleep(2)
                except Exception as e1:
                    print(f"No trobat 'Anunci de licitació'. S'intenta 'Anuncio de licitación'...")
                    try:
                        Anuncio_link = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.LINK_TEXT, "Anuncio de licitación"))
                        )
                        Anuncio_link.click()
                        time.sleep(3)
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
                        time.sleep(2)
                    except Exception as e2:
                        print(f"No trobat 'Anuncio de licitación'. S'intenta 'Adjudicació'...")
                        try:
                            Adjudicacio_link = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.LINK_TEXT, "Adjudicació"))
                            )
                            Adjudicacio_link.click()
                            time.sleep(3)
                            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
                            time.sleep(2)
                            print(f"No trobat 'Anunci de licitació' ni 'Anuncio de licitación', s'intenta 'Adjudicació' per expedient {codi_expedient}.")
                        except Exception as e3:
                            print(f"No trobat 'Anunci de licitació', 'Anuncio de licitación' ni 'Adjudicació' per expedient {codi_expedient}.")

                # BOTONS PDF
                try:
                    pdf_buttons = driver.find_elements(By.XPATH, "//button[contains(text(),'.pdf')]")
                    for pdf_button in pdf_buttons:
                        pdf_text = pdf_button.text.strip().lower()
                        if ".pdf" in pdf_text and is_relevant_pdf(pdf_text):
                            print(f"Descarregant PDF rellevant: {pdf_text}")
                            pdf_button.click()
                            time.sleep(3)
                            print(f"S'ha intentat descarregar el PDF rellevant amb el botó: {pdf_text}")
                        else:
                            print(f"Document ignorat (botó): {pdf_text}")
                except Exception as e:
                    print(f"Error durant la cerca i descàrrega de PDFs amb botons: {e}")

                # ENLLAÇOS PDF
                try:
                    pdf_links = driver.find_elements(By.XPATH, "//a[@href]")
                    print(f"S'han trobat {len(pdf_links)} enllaços amb href.")

                    for pdf_link in pdf_links:
                        pdf_text = pdf_link.text.strip().lower()
                        print(f"Enllaç trobat: {pdf_text}")

                        if ".pdf" in pdf_text and is_relevant_pdf(pdf_text):
                            pdf_url = pdf_link.get_attribute("href")
                            print(f"Descarregant PDF rellevant des de l'URL: {pdf_url}")

                            try:
                                driver.get(pdf_url)
                                print(f"S'ha iniciat la descàrrega del fitxer amb Selenium: {pdf_url}")
                                time.sleep(5)
                            except Exception as selenium_error:
                                print(f"Error durant la descàrrega amb Selenium: {selenium_error}")

                            try:
                                headers = {"User-Agent": "Mozilla/5.0"}
                                response = requests.get(pdf_url, headers=headers)
                                if response.status_code == 200:
                                    filename = os.path.join(carpeta_descargas, pdf_url.split('/')[-1])
                                    with open(filename, 'wb') as f:
                                        f.write(response.content)
                                    print(f"Descarregat correctament amb requests: {filename}")
                                else:
                                    print(f"No s'ha pogut descarregar el fitxer amb requests. Codi d'estat: {response.status_code}")
                            except Exception as requests_error:
                                print(f"Error durant la descàrrega amb requests: {requests_error}")
                        else:
                            print(f"Document ignorat (enllaç): {pdf_text}")
                except Exception as e:
                    print(f"Error durant la descàrrega dels enllaços PDF: {e}")

            finally:
                driver.quit()
    else:
        print("Les columnes 'CODI_EXPEDIENT' o 'ENLLAC_PUBLICACIO' no existeixen a l'arxiu.")

# Protecció per evitar execució automàtica quan s'importa
if __name__ == "__main__":
    descarregar_documents()
