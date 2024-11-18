from datetime import time
import random
import selenium
import selenium.webdriver
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
import selenium.webdriver.remote
import selenium.webdriver.remote.webelement
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

import logging

import time as tm
from .Donnees import Etat

logger = logging.getLogger(__name__)

class Navigateur:
    def __init__(self, token : str) -> None:
        self.token : str = token
        self.driver : webdriver = None
        self.text : str = ""
        
    
    def __enter__(self):
        return self

    def __exit__(self):
        self.driver.quit()

    def close(self) -> None:
        """
        Ferme le navigateur ouvert
        """
        self.driver.quit()
    
    def reset_navigateur(self) -> None:
        """
        créé une nouvelle instance de navigateur
        """
        chrome_options = Options()
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        chrome_options.add_argument("--headless")  # Mode headless activé
        chrome_options.add_argument("--headless")  # Exécute Chrome en mode headless
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)


        #chrome_options.add_argument("--start-maximized")  # Définit la taille de la fenêtre

        logger.info("Navigateur.reset_navigateur")

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        logger.info("Navigateur.reset_navigateur -> self.driver defini")
        logger.info("ChromeDriver Version:", self.driver.capabilities['chrome']['chromedriverVersion'])
        logger.info("Browser Version:", self.driver.capabilities['browserVersion'])

        self.driver.set_page_load_timeout(5)

    def getElement(self, selecteur : str, tps : int = 2, parent=None) -> selenium.webdriver.remote.webelement.WebElement:
        """
        Recupere un element d'une page web
        """
        if parent == None: parent = self.driver
        try:
            element : selenium.webdriver.remote.webelement.WebElement = WebDriverWait(parent, tps).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, selecteur))
            )
            return element  
        except:
            return None
        
    def getElements(self, selecteur : str, tps : int = 3,  parent=None) -> selenium.webdriver.remote.webelement.WebElement:
        """
        Recupere tout les element d'une page web
        """
        if parent is None:
            parent = self.driver
        try:
            elements = WebDriverWait(parent, tps).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selecteur))
                )            
            return elements
        except Exception as e:
            return None

    def start(self, l : str) -> bool:
        """
        Lance un driver avec le token de connexion
        True si token valide
        False sinon
        """
        try:
            logger.info("Navigateur.start")
            self.reset_navigateur()
            logger.info("Navigateur.start -> reset_navigateur ...")
            self.get(l)
            logger.info("Navigateur.start -> get ...")
            self.driver.set_page_load_timeout(20)
            logger.info(f"Navigateur.start -> token a definir {self.token}")
            self.setCookie('li_at', self.token, '.linkedin.com', '/')
            logger.info("Navigateur.start -> setCookie ...")
            return True
        except TimeoutException:
            logger.info("Timeout: La page a mis trop de temps à charger.")
            return False
        except Exception as e:
            logger.info(f"Erreur navigateurr: {e}")
            return False

    def setCookie(self, name, value, domain, path='/') -> None:
        """
        Initialise un cookie sur une page web
        """
        cookie = {'name': name, 'value': value, 'path': path, 'domain': domain}
        self.driver.add_cookie(cookie)
        self.driver.refresh()

    def get(self, l : str) -> None:
        """
        Se connecte a la page l
        """
        self.driver.get(l)
        

class LinkedInNavigateur(Navigateur):
    def __init__(self, token):
        super().__init__(token) 

    def connexion(self) -> Etat:
        """
        Envoi une demande de connexion a un Prospect
        """                       
        tm.sleep(10)
        div = self.getElement('.gcGTCzCIvipxmcCliFpucHQrjcAuIXmk          ', 10)
        children = div.find_elements(By.XPATH, "./*")  # ./* récupère les enfants directs

        button = None
        for child in children:
            if child.text in ['Se connecter', 'Suivre']:
                button = child
        
        if button is not None:
            if button.text == "Se connecter":
                button.click()
                accept = self.getElement(".artdeco-button.artdeco-button--2.artdeco-button--primary.ember-view.ml1", 10)
                if accept is not None:
                    tm.sleep(random.randint(0, 4))
                    accept.click()
                    return Etat.ON_HOLD
                return Etat.FAILURE
            elif button.text == "Suivre":
                all_boutons = self.getElements(".artdeco-dropdown__trigger.artdeco-dropdown__trigger--placement-bottom.ember-view.pvs-profile-actions__action.artdeco-button.artdeco-button--secondary.artdeco-button--muted.artdeco-button--2")
                bouton_plus = all_boutons[[e.text for e in all_boutons].index("Plus")]
                tm.sleep(random.randint(0, 3))
                bouton_plus.click() ## Trouve le bouton Plus et clic dessus

                se_connecter = self.driver.find_elements(By.XPATH, '//div[contains(@aria-label, "Invitez")]')
                se_connecter = se_connecter[[el.text for el in se_connecter].index("Se connecter")]
                tm.sleep(random.randint(0, 3))
                se_connecter.click() ## Trouve le bouton se connecter et clic dessus

                accept = self.getElement(".artdeco-button.artdeco-button--2.artdeco-button--primary.ember-view.ml1") ## Trouve le bouton de connexion
                if accept is not None:
                    tm.sleep(random.randint(0, 1))
                    accept.click()
                return Etat.ON_HOLD
            else:
                return Etat.FAILURE
        return Etat.FAILURE
    
    def getEtatsProspects(self) -> Etat:
        logger.info('LinkedInNavigateur.getEtatsProspects -> debut')
        try : 
            a = self.driver.find_element(By.XPATH, '//*[@id="global-nav"]/div/nav/ul/li[2]/a')
            tm.sleep(random.randint(0, 3))
            a.click()

            tm.sleep(random.randint(1, 3))

            t = self.driver.find_element(By.CSS_SELECTOR, '.display-flex.align-items-center.justify-space-between.pl5.pr2.cursor-pointer')
            # div1 = self.getElement(".mn-community-summary", 15)
            t.click()

            tm.sleep(random.randint(1, 2))
            div = self.getElement(".mn-community-summary__sub-section-nurture.artdeco-dropdown__item", 15)
            div.click()

            # ----- page recherché
            prospects = self.getElements('.ember-view.mn-connection-card__picture', 10)    

            return [e.get_attribute('href') for e in prospects]
        except Exception as e:
            logger.info(f"Erreur navigateurr: {e}")
            return False


    def envoiMessage(self, message : str) -> Etat:
        button = self.getElement(".artdeco-button.artdeco-button--2.artdeco-button--primary.ember-view.pvs-profile-actions__action", 10)
        if button.text == "Message":
            button.click()

            close = self.getElement(".msg-overlay-bubble-header__control.artdeco-button.artdeco-button--circle.artdeco-button--muted.artdeco-button--1.artdeco-button--tertiary.ember-view")

            tm.sleep(random.randint(4,8))
            m = self.getElements(".msg-s-message-list__event.clearfix") ## message des gens 

            if m != None:
                if len(m) > 0:            
                    if close is not None:
                        tm.sleep(random.randint(0,2))
                        close.click()
                    return Etat.SUCCESS

            r = self.getElement(".msg-form__contenteditable.t-14.t-black--light.t-normal.flex-grow-1.full-height.notranslate")  
            r.clear()          
            r.send_keys(message)

            button = self.getElement(".msg-form__send-btn.artdeco-button.artdeco-button--circle.artdeco-button--1.artdeco-button--primary.ember-view")
            tm.sleep(random.randint(1,3))
            button.click()

            if close is not None:
                tm.sleep(random.randint(0, 2))
                close.click()
            return Etat.SENT
