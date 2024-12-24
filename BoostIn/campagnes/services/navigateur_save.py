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
from selenium.webdriver import ActionChains
import undetected_chromedriver as uc

import logging
import zipfile

import time as tm
from .Donnees import Etat

logger = logging.getLogger(__name__)

# Configuration du proxy
def create_proxy_auth_extension(plugin_path=None):
    PROXY_HOST = '41.180.243.19'
    PROXY_PORT = 12323
    PROXY_USER = '14aa7ef9015e4'
    PROXY_PASS = 'ec8f923977'

    if plugin_path is None:
        plugin_path = 'proxy_auth_plugin.zip'

    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = f"""
    var config = {{
            mode: "fixed_servers",
            rules: {{
            singleProxy: {{
                scheme: "http",
                host: "{PROXY_HOST}",
                port: parseInt({PROXY_PORT})
            }},
            bypassList: ["localhost"]
            }}
        }};

    chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

    function callbackFn(details) {{
        return {{
            authCredentials: {{
                username: "{PROXY_USER}",
                password: "{PROXY_PASS}"
            }}
        }};
    }}

    chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {{urls: ["<all_urls>"]}},
                ['blocking']
    );
    """

    with zipfile.ZipFile(plugin_path, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

    return plugin_path

class Navigateur:
    def __init__(self, token : str) -> None:
        self.token : str = token
        self.driver : uc = None
        self.text : str = ""
        self.dernier_nom = None
        
    
    def __enter__(self):
        return self

    def __exit__(self):
        self.driver.quit()

    def close(self) -> None:
        """
        Ferme le navigateur ouvert
        """
        self.driver.quit()
    
    def reset_navigateur(self, use_proxy=True) -> None:
        """
        créé une nouvelle instance de navigateur
        """
        chrome_options = Options()
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        chrome_options.add_argument("--headless")  # Mode headless activé
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--incognito")
        width, height = random.randint(1200, 1920), random.randint(800, 1080)
        chrome_options.add_argument(f"--window-size={width},{height}")


        # chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        # chrome_options.add_experimental_option('useAutomationExtension', False)
        if use_proxy:
            proxy_auth_plugin_path = create_proxy_auth_extension()
            chrome_options.add_extension(proxy_auth_plugin_path)

        #chrome_options.add_argument("--start-maximized")  # Définit la taille de la fenêtre

        logger.info("Navigateur.reset_navigateur")

        self.driver = uc.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
            '''
        })
        self.driver.execute_cdp_cmd(
            'Emulation.setGeolocationOverride', {
                'latitude': 48.8566,  # Position Paris
                'longitude': 2.3522,
                'accuracy': 1
            }
        )
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.navigator.chrome = undefined;
            window.navigator.permissions.query = function(parameters) {
                return new Promise((resolve) => {
                    resolve({ state: 'prompt' });
                });
            };
            '''})

        logger.info("Navigateur.reset_navigateur -> self.driver defini")
        logger.info("ChromeDriver Version:", self.driver.capabilities['chrome']['chromedriverVersion'])
        logger.info("Browser Version:", self.driver.capabilities['browserVersion'])

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
            self.reset_navigateur(use_proxy=False)
            logger.info("Navigateur.start -> reset_navigateur ...")
            self.get(l)
            logger.info("Navigateur.start -> get ...")
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
    def connexion(self):
        """
        Envoi une demande de connexion a un Prospect
        """                       
        actions = ActionChains(self.driver)
        actions.move_by_offset(random.randint(0, 100), random.randint(0, 100)).perform()

        tm.sleep(random.randint(1, 6))

        self.dernier_nom = self.recuperer_nom()

        logger.info('debut')

        div = self.get_div_centre_action() 
        if div is None: return None
        
        children = div.find_elements(By.XPATH, "./*")  # ./* récupère les enfants directs

        button = None
        for child in children:
            logger.info(f"texte du bouton {child.text}")
            if child.text in ['Se connecter', 'Suivre', 'Accepter', 'En attente']:
                button = child
        
        if button is not None:
            actions = ActionChains(self.driver)
            actions.move_by_offset(random.randint(0, 100), random.randint(0, 100)).perform()
            if button.text == "Se connecter":
                button.click()
                accept = self.getElement(".artdeco-button.artdeco-button--2.artdeco-button--primary.ember-view.ml1", 10)
                if accept is not None:
                    actions = ActionChains(self.driver)
                    actions.move_by_offset(random.randint(0, 100), random.randint(0, 100)).perform()
                    tm.sleep(random.randint(1, 4))
                    accept.click()
                    return Etat.ON_HOLD
                return Etat.NOT_SENT
            elif button.text == "Suivre":
                bouton_plus = None
                for child in children:
                    logger.info(child.text)
                    if child.text == 'Plus':
                        bouton_plus = child
                # all_boutons = self.getElements(".artdeco-dropdown__trigger.artdeco-dropdown__trigger--placement-bottom.ember-view.pvs-profile-actions__action.artdeco-button.artdeco-button--secondary.artdeco-button--muted.artdeco-button--2")
                # bouton_plus = all_boutons[[e.text for e in all_boutons].index("Plus")]
                tm.sleep(random.randint(1, 3))
                bouton_plus.click() ## Trouve le bouton Plus et clic dessus

                se_connecter = self.driver.find_elements(By.XPATH, '//div[contains(@aria-label, "Invitez")]')
                se_connecter = se_connecter[[el.text for el in se_connecter].index("Se connecter")]
                actions = ActionChains(self.driver)
                actions.move_by_offset(random.randint(0, 100), random.randint(0, 100)).perform()

                tm.sleep(random.randint(1, 3))
                se_connecter.click() ## Trouve le bouton se connecter et clic dessus

                accept = self.getElement(".artdeco-button.artdeco-button--2.artdeco-button--primary.ember-view.ml1") ## Trouve le bouton de connexion
                if accept is not None:
                    tm.sleep(random.randint(1, 3))
                    accept.click()
                return Etat.ON_HOLD
            elif button.text == "Accepter":
                actions = ActionChains(self.driver)
                actions.move_by_offset(random.randint(0, 100), random.randint(0, 100)).perform()

                tm.sleep(random.randint(1, 6))
                button.click()
                return Etat.ACCEPTED
            elif button.text == 'En attente':
                return Etat.ON_HOLD
            else:
                return Etat.ACCEPTED
        else :
            logger.info("bouton est none.")                
        return Etat.FAILURE
    
    def recuperer_nom(self):
        titre = self.driver.title
        t1 = 0
        if ')' in titre:
            t1 = titre.index(') ')+2
        t2 = titre.index(' |')
        titre = titre[t1:t2]
        return titre
    
    def getEtatsProspects(self) :
        logger.info('LinkedInNavigateur.getEtatsProspects -> debut')
        if self.close_alert():
            try : 
                actions = ActionChains(self.driver)
                actions.move_by_offset(random.randint(0, 100), random.randint(0, 100)).perform()

                a = self.driver.find_element(By.XPATH, '//*[@id="global-nav"]/div/nav/ul/li[2]/a')
                tm.sleep(random.randint(1, 3))
                a.click()

                tm.sleep(random.randint(1, 3))

                liens = self.driver.find_elements(By.TAG_NAME, 'a')

                for l in liens:
                    if 'Relations' in l.text:
                        l.click()
                        break

                tm.sleep(random.randint(1, 2))
                actions = ActionChains(self.driver)
                actions.move_by_offset(random.randint(0, 100), random.randint(0, 100)).perform()

                # ----- page recherché
                prospects = self.getElements('.ember-view.mn-connection-card__picture', 10)    

                return [str(e.get_attribute('href'))[:-1] for e in prospects]
            except Exception as e:
                logger.info(f"Erreur navigateurr: {e}")
                return False
        return False


    def envoiMessage(self, message : str):
        tm.sleep(5)
        try:
            if message == '%$': ## pas d'envoi
                return None 
            if self.close_alert():            
                div = self.get_div_centre_action() 
                if div is None: return None

                children = div.find_elements(By.XPATH, "./*")  # ./* récupère les enfants directs

                button = None
                for child in children:
                    logger.info(f"texte du bouton {child.text}")
                    if child.text == 'Message':
                        button = child

                if button is not None:
                    button.click()
                    logger.info('bouton cliqué')

                    tm.sleep(random.randint(4,8))
                    m = self.getElements(".msg-s-message-list__event.clearfix") ## message des gens 
                    if m != None:
                        nom_conv = self.getElement(""".t-14.t-bold.hoverable-link-text.t-black""").text
                        nb_participant = []
                        for message_element in m:
                            try:
                                sub_element = message_element.find_element(By.CSS_SELECTOR, ".msg-s-message-group__profile-link.msg-s-message-group__name.t-14.t-black.t-bold.hoverable-link-text")
                                if sub_element.text not in nb_participant:
                                    nb_participant.append(sub_element.text)
                            except NoSuchElementException:
                                sub_element = None  

                        if nom_conv in nb_participant:            
                            logger.info('message deja envoyé')
                            logger.info(nom_conv)
                            logger.info(nb_participant)
                            close_button = self.getElements(".msg-overlay-bubble-header__control.artdeco-button.artdeco-button--circle.artdeco-button--muted.artdeco-button--1.artdeco-button--tertiary.ember-view")
                            for c in close_button:
                                if "Fermer votre conversation avec" in c.text:
                                    c.click()
                                    break
                            return Etat.SUCCESS
                        
                    r = self.getElement(".msg-form__msg-content-container.msg-form__message-texteditor.relative.flex-grow-1.display-flex")  

                    # Vérifiez que l'élément est interactif
                    if r.is_displayed() and r.is_enabled():
                        try:
                            actions = ActionChains(self.driver)
                            actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL)

                            # Simuler la touche Delete
                            actions.send_keys(Keys.DELETE)

                            # Exécuter les actions
                            actions.perform()
                            tm.sleep(random.randint(1, 2))

                            # Utiliser ActionChains pour envoyer un message
                            actions.send_keys(message).perform()
                        except Exception as e:
                            logger.info("il y a eu une erreur lors de la saisie")
                            logger.info(f"erreur : {e}")
                            return Etat.FAILURE
                        try:
                            button = self.getElement(".msg-form__send-button.artdeco-button.artdeco-button--1")
                            tm.sleep(random.randint(2, 4))
                            actions.move_to_element(button).click().perform()
                            logger.info('bouton cliqué')

                            close_button = self.getElements(".msg-overlay-bubble-header__control.artdeco-button.artdeco-button--circle.artdeco-button--muted.artdeco-button--1.artdeco-button--tertiary.ember-view")
                            for c in close_button:
                                if "Fermer votre conversation avec" in c.text:
                                    c.click()
                                    logger.info("fermé")
                                    break
                            return Etat.SENT
                        except Exception as e:
                            logger.info("il y a eu une erreur lors de l'appui du bouton")
                            logger.info(f'erreur {e}')
                            return Etat.FAILURE
                    else:
                        logger.info("L'élément n'est pas interactif.")
                        return Etat.FAILURE
        except Exception as e:
            logger.info(f'erreur fonction message : {e}')
            
    def close_alert(self):
        try:
            alert = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, 'artdeco-global-alert-container'))
            )

            bouton_close = alert.find_elements(By.CSS_SELECTOR, '.artdeco-global-alert__action.artdeco-button.artdeco-button--inverse.artdeco-button--2.artdeco-button--primary.ember-view')
            for c in bouton_close:
                if 'Refuser' in c.text:
                    c.click()
                    break
            return True
        except NoSuchElementException:
            return True
        except Exception as e:
            return False                

    def get_div_centre_action(self):
        try:
            wait = WebDriverWait(self.driver, 10)
            divs = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//button[contains(@aria-label, 'Plus d’actions')]")))

            for i, div in enumerate(divs):
                if div.text == 'Plus':
                    div_parent = div.find_element(By.XPATH, "..")
                    div_cible = div_parent.find_element(By.XPATH, "..")
                    return div_cible
        except Exception as e:
            return None
    
    def recuperer_reponse(self):
        """
        réalise des actions pour recuperer le nom des prospects ayant repondu
        """
        tm.sleep(5)
        if self.close_alert():
            messagerie = self.driver.find_elements(By.TAG_NAME, 'header')
            for m in messagerie:
                if m.text == 'Messagerie':
                    m.click()
                    break

        recherche = self.getElement(".msg-overlay-list-bubble-search")
        bouton_filtre = recherche.find_element(By.TAG_NAME, 'button')
        bouton_filtre.click()
        tm.sleep(1)

        div_element = self.driver.find_element(By.CSS_SELECTOR, ".artdeco-dropdown__content.msg-overlay-list-bubble__filters-dropdown-content.artdeco-dropdown--is-dropdown-element.artdeco-dropdown__content--has-arrow.artdeco-dropdown__content--arrow-right.artdeco-dropdown__content--justification-right.artdeco-dropdown__content--placement-bottom.ember-view")

        non_lus_button = div_element.find_element(By.XPATH, "//span[text()='Non lus']")
        non_lus_button.click()

        tm.sleep(4)

        conversation = self.driver.find_element(By.CSS_SELECTOR, ".msg-overlay-list-bubble__default-conversation-container")
        html_content = conversation.get_attribute("outerHTML")
        print(html_content)

        truncate = conversation.find_elements(By.CSS_SELECTOR, ".truncate")
        print(len(truncate))
        liste_prospect = []
        for t in truncate:
            if t.text not in liste_prospect:
                liste_prospect.append(t.text)

        return liste_prospect
