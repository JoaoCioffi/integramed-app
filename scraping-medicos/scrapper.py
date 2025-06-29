import requests
from bs4 import BeautifulSoup
import urllib.parse
import json

def loadHeaders(filePath='./headers.json'):
    # --- Carregamento de headers do arquivo JSON ---
    with open(filePath,'r',encoding='utf-8') as f:
        return json.load(f)

def readSpecialities(filePath='./especialidades.txt'):
    # --- Carregamento de especialidades do arquivo txt ---
    with open(filePath,'r',encoding='utf-8') as f:
        return [row.strip() for row in f if row.strip()]

def mountURL(speciality,page):
    # --- Construção correta da URL com base na página ---
    encoded=urllib.parse.quote_plus(speciality)
    if page==1:
        return (
            f'https://agendarconsulta.com/buscar/'
            f'autocomplete={encoded}&insurance=&city=&accepts_in_person=true&accepts_telemedicine=false'
        )
    else:
        return (
            f'https://agendarconsulta.com/buscar/'
            f'autocomplete={encoded}&city=&consultation_type=in_person&insurance=&page={page}'
        )

def getPageResult(html):
    # --- Verifica se a página possui resultados ou está vazia ---
    soup=BeautifulSoup(html,'html.parser')
    return not bool(soup.select_one('div.SearchList_empty-content__3YjGM'))

def scanSpeciality(speciality,headers,maxPage=500):
    # --- Varrer URLs de uma especialidade ---
    print('\n','-='*30,f'\n[{speciality}]')
    for page in range(1,maxPage + 1):
        url=mountURL(speciality,page)
        print('\n')
        print(f'Página: {page}\nURL: {url}')
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f'\n[HTTP ERROR] {response.status_code} na página {page}')
            break
        if not getPageResult(response.text):
            print(f'\n[INFO] Sem resultados. Encerrando busca para essa especialidade...')
            break

def main():
    headers=loadHeaders('./headers.json')
    specialities=readSpecialities('./especialidades.txt')
    for s in specialities:
        scanSpeciality(s,headers)

if __name__ == '__main__':
    main()