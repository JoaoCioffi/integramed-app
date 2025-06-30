from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium import webdriver
from bs4 import BeautifulSoup
import urllib.parse
import pandas as pd
import requests
import json
import time

def loadHeaders(filePath=None):
    # --- Carregamento de headers do arquivo JSON ---
    with open(filePath,"r",encoding="utf-8") as f:
        return json.load(f)
    
def readSpecialities(filePath=None):
    # --- Carregamento de especialidades do arquivo txt ---
    with open(filePath,"r",encoding="utf-8") as f:
        return [row.strip() for row in f if row.strip()]

def mountURL(speciality,page):
    # --- Construção correta da URL com base na página ---
    encoded=urllib.parse.quote_plus(speciality)
    if page == 1:
        return (
            f"https://agendarconsulta.com/buscar/"
            f"autocomplete={encoded}&insurance=&city=&accepts_in_person=true&accepts_telemedicine=false"
        )
    else:
        return (
            f"https://agendarconsulta.com/buscar/"
            f"autocomplete={encoded}&city=&consultation_type=in_person&insurance=&page={page}"
        )

def getPageResult(html):
    # --- Verifica se a página possui resultados ou está vazia ---
    soup=BeautifulSoup(html, "html.parser")
    return not bool(soup.select_one("div.SearchList_empty-content__3YjGM"))

def collectProfileURL(driver,listURL):
    # --- Coleta URLs dos perfis de cada médico ---
    driver.get(listURL)
    try:
        WebDriverWait(driver,10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR,"div[itemtype='https://schema.org/Physician']"))
        )
        blocks=driver.find_elements(By.CSS_SELECTOR,"div[itemtype='https://schema.org/Physician']")
        profileURL=[]
        for i in range(len(blocks)):
            blocks=driver.find_elements(By.CSS_SELECTOR,"div[itemtype='https://schema.org/Physician']")
            name_element=blocks[i].find_element(By.CSS_SELECTOR, "h3")
            driver.execute_script("arguments[0].click();",name_element)
            WebDriverWait(driver, 10).until(EC.url_contains("/perfil/"))
            profileURL.append(driver.current_url)
            driver.back()
            time.sleep(1)
        return profileURL
    except Exception as e:
        print(f"[ERRO] Falha ao processar {listURL}: {e}")
        return []

def cleanAddress(firstRow,secRow):
    # --- Realiza um tratamento para caso o endereço já contiver '-' ao final, para evitar registros errados ---
    firstRow=firstRow.strip()
    if firstRow.endswith("-"):
        return f"{firstRow} {secRow.strip()}"
    return f"{firstRow} - {secRow.strip()}"

def scrapeProfile(url,headers):
    # --- Coleta os dados: nome, crm, endereço, especialidade, contato (whatsapp) e procedimentos realizados ---
    response=requests.get(url,headers=headers)
    soup=BeautifulSoup(response.text,"html.parser")

    name=soup.select_one("h1, h2, div h1, div h2")
    name=name.text.strip() if name else "N/A"

    specialityRaw=soup.select_one("div span:-soup-contains('Médico')")
    speciality=specialityRaw.text.strip() if specialityRaw else "N/A"

    crmRaw=soup.find(string=lambda x: "CRM" in x)
    crm=f"CRM {crmRaw.split('CRM')[-1].strip()}" if crmRaw else "N/A"

    firstRow=soup.select_one("address > p:nth-of-type(1)")
    secRow=soup.select_one("address > p:nth-of-type(2)")
    address=cleanAddress(
        firstRow.text if firstRow else "",secRow.text if secRow else ""
    ) if (firstRow or firstRow) else "N/A"

    whatsappLinks=soup.select("a[href*='api.whatsapp.com']")
    collectedWppData=[a.get_text(strip=True) for a in whatsappLinks]
    whatsappContactInfo=", ".join(collectedWppData) if collectedWppData else "N/A"

    procedimentos = "N/A"
    faq_blocks = soup.select("div[style*='margin-bottom'] > p.MuiTypography-body1")
    for i, pergunta in enumerate(faq_blocks):
        if "Quais procedimentos" in pergunta.text:
            if i + 1 < len(faq_blocks):
                procedimentos = faq_blocks[i + 1].text.strip()
            break

    return {
        "nome": name,
        "especialidade": speciality,
        "crm": crm,
        "endereco": address,
        "numeros_whatsapp": whatsappContactInfo,
        "procedimentos": procedimentos,
        "url": url,
    }

def scanSpeciality(speciality,headers,driver,df,maxPage=50):
    # --- Função principal: une as demais (montagem de URL, scrape do perfil), une os dados num DataFrame pandas e salva em .csv ---
    print(f"\n[Coletando dados de: {speciality}]")
    for page in range(1,maxPage + 1):
        url=mountURL(speciality,page)
        print(f"\nPágina {page} - URL: {url}")
        response=requests.get(url,headers=headers)
        if response.status_code != 200:
            print(f"[HTTP ERROR] Página {page}: {response.status_code}")
            break
        if not getPageResult(response.text):
            print(f"\n[INFO] Sem resultados. Encerrando busca para essa especialidade...")
            break
    
        profileURL=collectProfileURL(driver,url)
        newData=[]
        for purl in profileURL:
            print(f"-> {purl}")
            data=scrapeProfile(purl,headers)
            newData.append(data)

        df_page=pd.DataFrame(newData)
        df=pd.concat([df,df_page],ignore_index=True)
        df.to_csv("medicos_raw.csv",index=False,encoding="utf-8-sig")

        print("\nDataFrame parcial (atualizado):")
        print(df.tail(len(newData)))
    return df

def main():
    headers=loadHeaders("./headers.json")
    specialities=readSpecialities("./especialidades.txt")
    df_total=pd.DataFrame()

    edge_options=Options()
    edge_options.add_argument("--log-level=3")
    edge_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    service=Service(executable_path="./msedgedriver.exe")
    driver=webdriver.Edge(service=service,options=edge_options)

    for s in specialities:
        df_total=scanSpeciality(s,headers,driver,df_total)

    driver.quit()
    print("\n✅ Coleta finalizada!")

if __name__ == "__main__":
    main()
