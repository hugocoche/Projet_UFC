"""

"""

from bs4 import BeautifulSoup
from collections import defaultdict
from selenium import webdriver
from rich.console import Console

import re
import pandas as pd

def _infos_principal_combattant(fiche_combattant, dictio):
    """
    Fonction qui extrait les informations principales d'un combattant
    """
    for item in fiche_combattant:
        if any(clss in ['hero-profile__division-title', 'hero-profile__division-body'] for clss in item.get('class', [])):
            text = item.text.strip()
            if ' (W-L-D)' in text:
                record, _ = text.split(' (')
                wins, losses, draws = record.split('-')
                dictio['Win'] = int(wins)
                dictio['Losses'] = int(losses)
                dictio['Draws'] = int(draws)
            else:
                dictio["Division"] = text
                if "Women's" in text:
                    dictio["Genre"] = "Female"
                else:
                    dictio["Genre"] = "Male"


def _combattant_actif(soup,dictio):
    if any('Actif' in tag.text for tag in soup.find_all("p", class_="hero-profile__tag")):
        dictio["Actif"] = True
    else :  
        dictio["Actif"] = False


def _bio_combattant(info_combattant, dictio, required):
    for item in info_combattant:
        label = item.find("div", class_="c-bio__label")
        text = item.find("div", class_="c-bio__text")
    
        if label and text:
            if label.text.strip() in required:
                if text.find("div"):
                    text = text.find("div") #cas de couche caché 
                val = text.text.strip() if text else None
                dictio[label.text.strip()] = float(val) if bool(re.fullmatch(r'\d+(\.\d+)?',val)) else val


def _tenant_titre(soup,dictio):
    if any('Title Holder' in tag.text for tag in soup.find_all("p", class_="hero-profile__tag")):
        dictio["Title_holder"] = True
    else : 
        dictio["Title_holder"] = False


def _stats_combattant(soup,dictio) :
    liste_objective = ['Permanent', 'Clinch', 'Sol', 'KO/TKO', 'DEC', 'SUB']
    groups = soup.find_all("div", class_="c-stat-3bar__group")
    if groups:
        for group in groups:
            label = group.find("div", class_="c-stat-3bar__label") #case bas gauche et bas droite de la section stats
            value = group.find("div", class_="c-stat-3bar__value")
            if label and value:
                cleaned_value = re.sub(r'\s*\(.*?\)', '', value.text).strip()
                dictio[label.text.strip()] = int(cleaned_value)
            else:
                dictio[label.text.strip()] = None
    else :
        for obj in liste_objective:
            dictio[obj] = None


def _stats_corps_combattant(soup,dictio):
    # ['sig_str_head', 'sig_str_body', 'sig_str_leg']
    body_part = ["head", "body", "leg"]
    for part in body_part:
        small_soup = soup.find("g", id=f"e-stat-body_x5F__x5F_{part}-txt")
        if small_soup:
            texts = small_soup.find_all('text')
            if len(texts) > 1:
                dictio[f"sig_str_{part}"] = int(texts[1].text.strip()) # 1 On prend l'entier , mettre 0 pour prendre le pourcentage
        else:
            dictio[f"sig_str_{part}"] = None


def _pourcentage_touche_takedown(soup,dictio):
    liste_objective = ["Précision_saisissante", "Précision_de_Takedown"]
    percentage_text = soup.select('svg.e-chart-circle > title')
    pattern = re.compile(r'([a-zA-Zéèêàç\s]+)(\d+%)')

    if not percentage_text:
        dictio["Précision_saisissante"] = None
        dictio["Précision_de_Takedown"] = None
    else :
        for chaine in percentage_text:
            match = pattern.match(chaine.text)
            if match:
                mots = match.group(1).strip().replace(' ', '_')
                pourcentage = match.group(2).strip()
                dictio[mots] = float(pourcentage.rstrip('%'))     
        mot_manquants = [mot for mot in liste_objective if mot not in dictio.keys()]
        if mot_manquants:
            dictio[f"{mot_manquants[0]}"] = None


def _extraire_temps(element):
    """
    fonction qui extrait le temps de combat moyen
    """
    if not element:
        return None
    try:
        if element.find("div", class_="c-stat-compare__percent"):
            element.find("div", class_="c-stat-compare__percent").extract()
        text = element.text.strip()
        return float(re.sub(r'[^\d.]+', '', text))
    except ValueError:
        return None

def _convert_minutes(time_str):
    try:
        minutes, secondes = map(int, time_str.split(':'))
        return minutes * 60 + secondes
    except ValueError:
        return None


def _mesures_combattant(soup, dictio):
    liste_objective = [
        'Sig. Str. A atterri', 'Sig. Frappes Encaissées', 
        'Takedown avg', 'Envoi avg', 
        'Sig. Str.défense', 'Défense de démolition', 
        'Knockdown Avg', 'Temps de combat moyen'
    ]

    groups = soup.find_all("div", class_="c-stat-compare__group")

    temp_data = {}

    for group in groups:
        label = group.find("div", class_="c-stat-compare__label")
        value = group.find("div", class_="c-stat-compare__number")

        if label:
            label_text = label.text.strip()
            if value:
                value_text = value.text.strip()
                if ":" in value_text:  
                    temp_data[label_text] = _convert_minutes(value_text)
                else:
                    temp_data[label_text] = _extraire_temps(value)
            else:
                temp_data[label_text] = None  

    for obj in liste_objective:
        dictio[obj] = temp_data.get(obj, None) # Pour eviter les eventuelles decalages

def extraire_info_combattant(soup:BeautifulSoup) -> dict:
    """
    Permet d'extraire les informations d'un combattant a partir d'un objet BeautifulSoup

    Args:
        soup (BeautifulSoup): Objet BeautifulSoup de la page web du combattant
    """
    dictio = defaultdict(str)
    recap_combattant = soup.select_one("div.hero-profile > div.hero-profile__info")
    info_combattant = soup.select("div.c-bio__field")
    fiche_combattant, cbt_name = recap_combattant.find_all("p"), recap_combattant.find("h1").text
    required = ["Style de combat","Âge","La Taille","Poids","Reach","Portée de la jambe"]
    dictio['Name'] = cbt_name

    _infos_principal_combattant(fiche_combattant, dictio)
    _combattant_actif(soup,dictio)
    _bio_combattant(info_combattant, dictio,required)
    _tenant_titre(soup,dictio)
    _stats_combattant(soup,dictio)
    _stats_corps_combattant(soup,dictio)
    _pourcentage_touche_takedown(soup,dictio)
    _mesures_combattant(soup,dictio)

    return dictio

    
if __name__ == "__main__":

    console = Console

    driver = webdriver.Chrome()

    url = "https://www.ufc.com/athlete/brandon-moreno"

    driver.get(url)

    driver.implicitly_wait(10)

    html_content = driver.page_source

    driver.quit()

    soup = BeautifulSoup(html_content, "html.parser")

    dictio = extraire_info_combattant(soup)

    data = pd.dataframe(dictio)

    console.print()