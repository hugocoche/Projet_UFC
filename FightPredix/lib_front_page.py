"""

"""

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException
from warnings import warn
from rich.console import Console
from FightPredix import extraire_info_combattant

import re
import time
import pandas as pd


def _recolte_pages_combattants(soup):
    elements = soup.find_all("a", href = re.compile(r'/athlete/[\w]+-[\w]+') ,class_="e-button--black")
    hrefs = [f'https://www.ufc.com{element['href']}' for element in elements]
    return hrefs



def _visite_page_combattant(driver, url):
    driver.get(url)
    time.sleep(1)
    html_content = driver.page_source
    soup = BeautifulSoup(html_content, "html.parser")
    dictio = extraire_info_combattant(soup)
    return dictio



def _click_chargement_plus(main_driver):
    element = WebDriverWait(main_driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[@title='Load more items']"))
    )
    
    main_driver.execute_script("arguments[0].scrollIntoView(true);", element)

    time.sleep(1)

    actions = ActionChains(main_driver)
    actions.move_to_element(element).click().perform()

    time.sleep(2)



def _deja_present(data : pd.DataFrame, url : str) -> bool:
    pattern = re.compile(r'/athlete/([\w]+-[\w]+)')
    match = pattern.search(url)
    nom = match.group(1).replace('-', ' ')
    if nom in data['Name'].values:
        return True
    return False



def page_principal(main_driver : webdriver , Data : pd.DataFrame=None, essais :int=None) -> pd.DataFrame:
    """
    Fonction permettant de recolter les informations des combattants de l'UFC

    Args:
        main_driver (webdriver): Objet webdriver de la page principale
        Data (pd.Dataframe, optional): Dataframe contenant les informations des combattants deja recoltees. None par default.
        essais (int, optional): Nombre de tentatives. None par default.
    """

    result = []
                # Wrapper
    hrefs = []

    if Data is None:
        Data = pd.DataFrame(columns=['Name'])

    def _page_principal_sub(main_driver, essais):

        if essais :
            essais += 1
            print(f"Attempt {essais}")
            if essais == 3:
                main_driver.quit()
                return pd.concat([Data, pd.DataFrame(result)], ignore_index=True)
        try :

            front_content = main_driver.page_source

            front_soup = BeautifulSoup(front_content, "html.parser")

            temp_liste = _recolte_pages_combattants(front_soup)

            sub_driver = webdriver.Chrome()

            for url in temp_liste:
                if url not in hrefs and not _deja_present(Data, url):
                    dictio = _visite_page_combattant(sub_driver, url)
                    result.append(dictio)
                    hrefs.append(url)

            sub_driver.quit()  

            _click_chargement_plus(main_driver)

            return _page_principal_sub(main_driver,essais)
            
        except TimeoutException:
            warn("TimeoutException : Le bouton de chargement n'a pas ete trouve. Fin de la pagination.")
        except WebDriverException as e:
            warn(f"Erreur WebDriver : {e}")
        except Exception as e:
            warn(f"Erreur inattendue : {e}")
            raise
        finally:
            main_driver.quit()

        return pd.concat([Data, pd.DataFrame(result)], ignore_index=True)

    return _page_principal_sub(main_driver, essais)



if __name__ == "__main__":

    console = Console()

    essais = 1
    
    main_driver = webdriver.Chrome()

    main_driver.get("https://www.ufc.com/athletes/all?filters%5B0%5D=status%3A23")

    test = page_principal(main_driver, essais= essais)

    console.print(test)