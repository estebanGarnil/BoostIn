import asyncio
from playwright.async_api import async_playwright
import random
import math
import os

import logging

import redis
from django.conf import settings


logger = logging.getLogger(__name__)

class Navigateur:
    def __init__(self, user_data_dir : str, canal : str) -> None:
        self.driver = None
        self.text: str = ""
        self.dernier_nom = None
        self.user_data_dir = os.path.abspath(user_data_dir)
        self.__canal : str = canal

        self.page = None
        self.browser = None
        self.context = None
        self.last_mouse_position = {'x': 0, 'y': 0}  # Dernière position de la souris
        self.lock = asyncio.Lock()

        self.user_data_dir = self.choisir_ou_creer_session(user_data_dir)
    
    def send_on_canal(self, message):
        client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
        channel_name = self.__canal
        client.publish(channel_name, message)

    def listen_on_canal(self):
        logger.info("en train d'attendre la reponse")
        client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
        pubsub = client.pubsub()

        pubsub.subscribe(self.__canal)

        for message in pubsub.listen():
            if message['type'] == 'message':  # Filtrer uniquement les messages
                logger.info("reponse reçu")
                return message['data'].decode('utf-8')

    def choisir_ou_creer_session(self, session_name: str, base_dir: str = './sessions') -> str:
        """
        Choisit ou crée une session utilisateur selon le nom donné.
        
        :param session_name: Le nom de la session utilisateur.
        :param base_dir: Le répertoire de base pour les sessions utilisateur.
        :return: Le chemin complet du dossier de la session utilisateur.
        """
        session_dir = os.path.join(base_dir, session_name)
        if not os.path.exists(session_dir):
            logger.info(f"La session '{session_name}' n'existe pas. Création d'une nouvelle session.")
            os.makedirs(session_dir, exist_ok=True)
        else:
            logger.info(f"La session '{session_name}' existe déjà. Utilisation de la session existante.")
        return session_dir

    async def stop(self):
        try:
            if self.page is not None:
                await self.page.close()
            if self.context is not None:
                await self.context.close()
            if self.browser is not None:
                await self.browser.close()
        except Exception as e:
            logger.info(f"Erreur lors de la fermeture du navigateur : {str(e)}")
        finally:
            if hasattr(self, 'playwright') and self.playwright is not None:
                await self.playwright.stop()
    
    async def get_new_page(self, url):
        await self.page.goto(url)
    
    async def start(self, lien):
        self.playwright = await async_playwright().start()

        logger.info(f"user_data_dir = {self.user_data_dir}")

        self.context = await self.playwright.chromium.launch_persistent_context(
        user_data_dir=self.user_data_dir,
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
            '--disable-gpu',
            '--disable-infobars',
            '--window-size=1920,1080',
            '--lang=fr-FR',
            '--disable-extensions',
        ],
        proxy={
            'server': '41.180.243.19:12323',  # Remplace par l'adresse et le port du proxy
            'username': '14aa7ef9015e4',  # Remplace par le nom d'utilisateur du proxy (si nécessaire)
            'password': 'ec8f923977'  # Remplace par le mot de passe du proxy (si nécessaire)
        },
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        viewport={'width': random.randint(1900, 1920), 'height': random.randint(1040, 1080)},
        locale="fr-FR",
        timezone_id="Europe/Paris"
        )

        await self.context.tracing.start(screenshots=True, snapshots=True, sources=True)

        # await self.setCookie(name="li_at", value=self.token, domain=".linkedin.com", path='/')

        self.page = await self.context.new_page()
        # await stealth_async(self.page)

        await self.page.goto(lien)
        
        await self.page.evaluate("""
            delete navigator.__proto__.webdriver;
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        await self.context.set_extra_http_headers({
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Upgrade-Insecure-Requests": "1"
            
        })

        await self.context.add_init_script('''() => {
                                           
            Object.defineProperty(navigator, 'userAgentData', {
            get: () => ({ 
                brands: [{ brand: 'Google Chrome', version: '131' }, { brand: 'Chromium', version: '131' }],
                mobile: false,
                platform: 'Windows'
            }) 
            });
                                           
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                configurable: false, // Rend la modification impossible
                enumerable: true
            });
            // Supprime webdriver de navigator
            delete navigator.__proto__.webdriver;
                        
            // Simuler chrome object
            window.chrome = {
                runtime: {},
                app: { isInstalled: false },
                webstore: { onInstallStageChanged: {}, onDownloadProgress: {} },
                csi: function() { return {}; },
                loadTimes: function() { return {}; },
                runtime: { PlatformOs: 'win' }
            };

            // Empêcher la détection du userAgentData
            Object.defineProperty(navigator, 'userAgentData', { 
                get: () => ({ 
                    brands: [{ brand: 'Google Chrome', version: '131' }, { brand: 'Chromium', version: '131' }],
                    mobile: false,
                    platform: 'Windows'
                }) 
            });

            // Empêcher la détection de permissions (simulateur de "Toujours autoriser")
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' 
                    ? Promise.resolve({ state: 'granted' }) 
                    : originalQuery(parameters)
            );

            // Empêcher la détection de plugins
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            
            // Empêcher la détection de langues
            Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr'] });

            // Simuler le support de WebGL
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function (parameter) {
                if (parameter === 37445) return 'Intel Open Source Technology Center';
                if (parameter === 37446) return 'Mesa DRI Intel(R) HD Graphics 620 (Kaby Lake GT2)';
                return getParameter(parameter);
            };
        }''')

        # Injecter un style et un élément de curseur dans la page
        await self.page.evaluate('''
            const cursor = document.createElement('div');
            cursor.id = 'custom-cursor';
            cursor.style.width = '20px';
            cursor.style.height = '20px';
            cursor.style.borderRadius = '50%';
            cursor.style.backgroundColor = 'red';
            cursor.style.position = 'absolute';
            cursor.style.top = '0';
            cursor.style.left = '0';
            cursor.style.zIndex = '9999';
            cursor.style.pointerEvents = 'none';  // Pour que le curseur n'interfère pas avec la page
            document.body.appendChild(cursor);
        ''')

        await self.page.screenshot(path="screenshot.png", full_page=True)



    async def setCookie(self, name, value, domain, path='/'):
        if self.context is not None:
            await self.context.add_cookies([{
                'name': name,
                'value': value,
                'domain': domain,
                'path': path,
                'httpOnly': True,
                'secure': True,
                'sameSite': 'Lax'
            }])

    async def simulate_scroll_with_wheel_random(self):
        scrolled = 0
        for i in range(random.randint(2, 4)):
            if i > 0:
                total_distance = random.uniform(-1000, 2000)
            else:
                total_distance = random.uniform(800, 2300)
            while scrolled < total_distance:
                distance = random.randint(10, 50)
                await self.page.mouse.wheel(0, distance)
                scrolled += distance
                await asyncio.sleep(random.uniform(0.01, 0.05))

    async def get_current_mouse_position(self):
        position = self.last_mouse_position  # Utiliser la dernière position connue
        logger.info(f"Position actuelle de la souris : ({position['x']}, {position['y']})")
        return position['x'], position['y']
    
        
    async def type_like_human(self, text, min_delay=0.05, max_delay=0.3):
        """
        Simule une saisie humaine dans un champ de texte.
        
        :param page: L'instance de la page Playwright.
        :param selector: Le sélecteur CSS ou XPath du champ de saisie.
        :param text: Le texte à saisir.
        :param min_delay: Le délai minimum entre chaque saisie de caractère.
        :param max_delay: Le délai maximum entre chaque saisie de caractère.
        """
        try:
            for char in text:
                await self.page.keyboard.type(char, delay=random.uniform(min_delay * 1000, max_delay * 1000))
        except Exception as e:
            logger.info(f"Erreur lors de la saisie du texte '{text}': {str(e)}")

    async def human_like_mouse_move(self, start_x, start_y, end_x, end_y, duration=2, steps=None):
        if steps is None:
            steps = random.randint(100, 150)
        
        x = start_x
        y = start_y

        dx = (end_x - start_x) / steps
        dy = (end_y - start_y) / steps

        for i in range(steps):
            x += dx + random.uniform(-2, 2)
            y += dy + random.uniform(-2, 2)
            curve_offset_x = math.sin(i / steps * math.pi) * random.uniform(-10, 10)
            curve_offset_y = math.cos(i / steps * math.pi) * random.uniform(-10, 10)
            new_x = x + curve_offset_x
            new_y = y + curve_offset_y

            await self.page.mouse.move(new_x, new_y)
            await self.page.evaluate(f'''
                const cursor = document.getElementById('custom-cursor');
                cursor.style.transform = `translate({x}px, {y}px)`;
            ''')
            self.last_mouse_position = {'x': new_x, 'y': new_y}  # Mettre à jour la dernière position
            await asyncio.sleep(random.uniform(duration / steps * 0.8, duration / steps * 1.2))

    async def move_to_element_and_click(self, selector):
        try:
            if isinstance(selector, str):
                element_handle = await self.page.locator(selector).bounding_box()
            else:
                element_handle = await selector.bounding_box()

            if element_handle is None:
                logger.info(f"Élément non trouvé avec le sélecteur {selector}")
                return

            offset_x = random.uniform(-element_handle['width'] / 4, element_handle['width'] / 4)
            offset_y = random.uniform(-element_handle['height'] / 4, element_handle['height'] / 4)

            x = element_handle['x'] + element_handle['width'] / 2 + offset_x
            y = element_handle['y'] + element_handle['height'] / 2 + offset_y

            logger.info(f"Coordonnées calculées pour l'élément : x={x}, y={y}")

            current_x, current_y = await self.get_current_mouse_position()
            if current_x is None or current_y is None:
                current_x, current_y = 0, 0

            logger.info(f"Position actuelle de la souris: x={current_x}, y={current_y}")

            await self.human_like_mouse_move(current_x, current_y, x, y, duration=random.uniform(1, 2), steps=50)
            await asyncio.sleep(random.uniform(0.2, 0.8))

            jitter_x = random.uniform(-2, 2)
            jitter_y = random.uniform(-2, 2)

            final_x = x + jitter_x
            final_y = y + jitter_y

            self.last_mouse_position = {'x': final_x, 'y': final_y}  # Mettre à jour la dernière position

            logger.info(f"Clique sur l'élément au point ({final_x}, {final_y}) avec jitter ({jitter_x}, {jitter_y})")

            await self.page.mouse.click(final_x, final_y, delay=random.randint(50, 150))

            await asyncio.sleep(random.uniform(2, 4))

        except Exception as e:
            logger.info(f"Erreur lors de l'exécution de move_to_element_and_click: {str(e)}")

    async def is_element_visible(self, selector):
        """
        Vérifie si l'élément est visible dans le viewport sans scroller.
        
        :param page: l'objet Playwright page
        :param selector: le sélecteur CSS ou XPath de l'élément à vérifier
        :return: True si l'élément est visible, False sinon
        """
        try:
            # Obtenez les dimensions du viewport
            viewport_size = await self.page.viewport_size()
            viewport_height = viewport_size['height']
            viewport_width = viewport_size['width']
            
            # Récupérez la position et les dimensions de l'élément
            bounding_box = await self.page.locator(selector).bounding_box()
            
            if bounding_box is None:
                logger.info(f"Impossible de trouver l'élément avec le sélecteur {selector}")
                return False

            element_top = bounding_box['y']
            element_bottom = bounding_box['y'] + bounding_box['height']
            element_left = bounding_box['x']
            element_right = bounding_box['x'] + bounding_box['width']

            # Vérifiez si l'élément est dans le viewport
            is_fully_visible = (
                element_top >= 0 and 
                element_bottom <= viewport_height and 
                element_left >= 0 and 
                element_right <= viewport_width
            )

            if is_fully_visible:
                logger.info(f"L'élément {selector} est visible.")
                return True
            else:
                logger.info(f"L'élément {selector} n'est pas visible. (Position y: {element_top}, Hauteur du viewport: {viewport_height})")
                return False
                
        except Exception as e:
            logger.info(f"Erreur lors de la vérification de la visibilité de l'élément : {e}")
            return False

    async def scroll_until_visible(self, selector, step=100, vitesse=0.1):
        """
        Scrolle la page jusqu'à ce que l'élément soit visible.
        
        :param page: L'instance de la page Playwright
        :param selector: Le sélecteur CSS ou XPath de l'élément à atteindre
        :param step: Le pas du scroll à chaque itération (en pixels)
        :param vitesse: Le délai entre chaque itération
        """
        try:
            for i in range(100):  # Nombre maximum de tentatives
                is_visible = await self.page.locator(selector).is_visible()
                
                if is_visible:
                    logger.info(f"✅ L'élément {selector} est maintenant visible.")
                    return
                
                await self.page.evaluate(f'window.scrollBy(0, {step});')
                await asyncio.sleep(vitesse)
                logger.info(f"Défilement étape {i + 1} de {step} pixels.")

        except Exception as e:
            logger.info(f"Erreur lors du scroll jusqu'à la visibilité : {str(e)}")

    async def get_viewport_size(self):
        """
        Récupère la taille de la fenêtre (viewport) de la page.
        
        :param page: L'instance de la page Playwright
        :return: La largeur et la hauteur du viewport
        """
        try:
            viewport_size = self.page.viewport_size  # Accès direct à la propriété
            width = viewport_size['width']
            height = viewport_size['height']
            logger.info(f"Largeur du viewport : {width}px, Hauteur du viewport : {height}px")
            return width, height
        except Exception as e:
            logger.info(f"Erreur lors de la récupération de la taille du viewport : {str(e)}")
            return None, None
    
    async def get_selector_location(self, selector):
        try:
            if isinstance(selector, str):
                bounding_box = await self.page.locator(selector).bounding_box()
            else:
                bounding_box = selector
            
            if bounding_box is None:
                logger.info(f"Impossible de localiser l'élément avec le sélecteur {selector}")
                return None
            
            x = bounding_box['x']
            y = bounding_box['y']
            width = bounding_box['width']
            height = bounding_box['height']

            sides = {
                'left': x,
                'top': y,
                'right': x + width,
                'bottom': y + height
            }

            logger.info(f"Sides de l'élément {selector} : {sides}")
            return sides
        except Exception as e:
            logger.info(f"Erreur lors de la récupération des côtés de l'élément : {str(e)}")
            return None

    async def is_element_in_viewport(self, selector):
        """
        Vérifie si l'élément est entièrement visible dans le viewport.
        
        :param page: L'instance de la page Playwright
        :param selector: Le sélecteur CSS ou XPath de l'élément
        :return: True si l'élément est visible, False sinon
        """
        try:
            # Attendez que l'élément soit présent
            await self.page.wait_for_selector(selector, timeout=10000)
            
            # Obtenez les côtés de l'élément
            sides = await self.get_selector_location(selector)
            if sides is None:
                return False

            # Obtenez la taille du viewport
            viewport_width, viewport_height = await self.get_viewport_size()

            # Vérifiez si l'élément est visible dans le viewport
            is_in_viewport = (
                sides['left'] >= 0 and
                sides['top'] >= 0 and
                sides['right'] <= viewport_width and
                sides['bottom'] <= viewport_height
            )

            if is_in_viewport:
                logger.info(f"✅ L'élément {selector} est visible dans le viewport.")
            else:
                logger.info(f"❌ L'élément {selector} n'est pas visible dans le viewport.")
            
            return is_in_viewport
        except Exception as e:
            logger.info(f"Erreur lors de la vérification de la visibilité de l'élément : {str(e)}")
            return False

    async def simulate_natural_scroll(self, total_distance=2000, max_step=50, min_step=10, min_pause=0.02, max_pause=0.1):
        """
        Simule un défilement naturel de la page de haut en bas.
        
        :param page: L'objet page de Playwright.
        :param total_distance: La distance totale à parcourir (en pixels).
        :param max_step: La distance maximale parcourue à chaque étape.
        :param min_step: La distance minimale parcourue à chaque étape.
        :param min_pause: La pause minimale (en secondes) entre les étapes.
        :param max_pause: La pause maximale (en secondes) entre les étapes.
        """
        scrolled_distance = 0
        while scrolled_distance < total_distance:
            # Calculer la distance aléatoire de défilement pour cette étape
            scroll_step = random.randint(min_step, max_step)
            
            # Vérifier que la distance restante est suffisante
            if scrolled_distance + scroll_step > total_distance:
                scroll_step = total_distance - scrolled_distance
            
            # Simuler le défilement avec la roulette de la souris
            await self.page.mouse.wheel(0, scroll_step)
            
            # Ajouter la distance au total
            scrolled_distance += scroll_step
            
            # Pause aléatoire pour rendre le défilement plus naturel
            pause_time = random.uniform(min_pause, max_pause)
            await asyncio.sleep(pause_time)

    async def scroll_to_element(self, selector):
        """
        Définit un défilement naturel pour amener l'élément spécifié dans le viewport.
        
        :param selector: Le sélecteur de l'élément cible.
        """
        try:
            # Attendre que l'élément soit présent dans la page
            await self.page.wait_for_selector(selector, timeout=10000)
            
            # Vérifiez si l'élément est déjà visible dans le viewport
            if await self.is_element_in_viewport(selector):
                logger.info(f"✅ L'élément {selector} est déjà visible dans le viewport.")
                return

            # Récupérer la position (bounding box) de l'élément
            sides = await self.get_selector_location(selector)
            if sides is None:
                logger.info(f"❌ Impossible de trouver l'élément {selector}.")
                return

            # Récupérer la taille du viewport
            _, viewport_height = await self.get_viewport_size()

            # Calculer la distance à scroller
            distance_to_scroll = sides['top'] - (viewport_height / 2)  # On place l'élément au centre du viewport
            logger.info(f"Distance calculée pour atteindre {selector} : {distance_to_scroll}px")
            
            if distance_to_scroll > 0:
                # Scroll vers le bas
                await self.simulate_natural_scroll(total_distance=distance_to_scroll)
            else:
                # Scroll vers le haut (inversé)
                distance_to_scroll = abs(distance_to_scroll)
                while distance_to_scroll > 0:
                    scroll_step = random.randint(10, 50)
                    if distance_to_scroll - scroll_step < 0:
                        scroll_step = distance_to_scroll
                    await self.page.mouse.wheel(0, -scroll_step)  # Défilement vers le haut (valeur négative)
                    distance_to_scroll -= scroll_step
                    await asyncio.sleep(random.uniform(0.02, 0.1))  # Pause aléatoire entre les défilements

            # Vérifier à nouveau si l'élément est visible
            if await self.is_element_in_viewport(selector):
                logger.info(f"✅ L'élément {selector} est maintenant visible dans le viewport.")
            else:
                logger.info(f"❌ L'élément {selector} n'a pas pu être amené dans le viewport.")
        except Exception as e:
            logger.info(f"Erreur dans scroll_to_element pour {selector} : {str(e)}")

    async def press_enter_key(self):
        await self.page.keyboard.press('Enter')
    
    async def press_tab_key(self):
        await self.page.keyboard.press('Tab')

    async def wait_natural(self):
        await asyncio.sleep(random.uniform(1, 4))

class UpgradeChromeSessionNavigateur(Navigateur):
    """
    Rendre les sessions chromes moins détéctable.
    -> se connecter a certains site web pour augmenter empreinte numérique

    """
    def __init__(self, utilisateur, canal):
        super().__init__(utilisateur, canal)


    async def navigate_on_google(self):
        if await self.detect_rules_google():
            await self.scroll_to_element('//html/body/div[2]/div[2]/div[3]/span/div/div/div/div[3]/div[1]/button[2]')
            await self.move_to_element_and_click('//html/body/div[2]/div[2]/div[3]/span/div/div/div/div[3]/div[1]/button[2]')

        await self.move_to_element_and_click("//html/body/div[1]/div[3]/form/div[1]/div[1]/div[1]/div[1]/div[2]/textarea")

    async def detect_rules_google(self):
        try:
            await self.page.wait_for_selector('text="Avant d\'accéder à Google"', timeout=5000)
            logger.info("Le champ 'Avant d'accéder à Google' est présent sur la page.")
            return True
        except Exception as e:
            logger.info(f"Le champ 'Avant d'accéder à Google' n'est pas présent sur la page. {e}")
            return False

    async def go_to_url(self, name, url):
        await self.navigate_on_google()
        await self.type_like_human(name)
        await self.press_enter_key()
        await asyncio.sleep(2, 4)

        element = self.page.locator(f'text="{url}"')
        logger.info(await element.get_attribute('class'))
        # links = await self.page.locator("a").all()
        # for l in links:
        #     try:

        #         href = await l.get_attribute("href")
        #         logger.info(href)
        #         if url in href:
        #             locator = l
        #             logger.info("element trouvé")
        #             logger.info(l)
        #             break
        #     except Exception as e:
        #         logger.info(e)

        await asyncio.sleep(random.uniform(1, 3))
        await self.move_to_element_and_click(element)

class LinkedInNavigateur(UpgradeChromeSessionNavigateur):
    def __init__(self, user_data_dir, canal):
        super().__init__(user_data_dir, canal)

    async def get_etats_prospects(self):
        """
        Recupere les dernieres acceptations de connexion sur linkedIn
        :return: List[str] -> le lien relatif de chaque prospect s'etant connecté recement
        """
        await asyncio.sleep(random.uniform(1, 3))

        await self.simulate_scroll_with_wheel()
        
        selecteur = '//*[@id="global-nav"]/div/nav/ul/li[2]'
        await self.move_to_element_and_click(selecteur)

        selecteur = 'xpath=/html/body/div[7]/div[3]/div/div/div/div/div[2]/div/div/div/div/div/div/section/div/div'
        await self.move_to_element_and_click(selecteur)

        liens = await self.page.locator("a").all()
        for l in liens:
            if 'Relations' in await l.text_content():
                selecteur = l
                break

        await self.move_to_element_and_click(selecteur)

        await asyncio.sleep(3)

        selecteur = '.ember-view.mn-connection-card__picture'

        prospects = await self.page.locator(selector=selecteur).all()

        await self.page.wait_for_timeout(10)  # 10 secondes pour voir ce qui se passe

        await asyncio.sleep(3)

        return [await e.get_attribute('href') for e in prospects]


    async def get_reponse(self):
        """
        Recupere les dernieres reponses non lues sur linkedIn
        :return: List[str] -> liste des noms des correspondant -> message non lues
        """
        await asyncio.sleep(random.uniform(1, 4))
        await self.simulate_scroll_with_wheel()
        await asyncio.sleep(random.uniform(0.5, 4))

        selector = '//*[@id="global-nav"]/div/nav/ul/li[4]' ## messagerie
        await self.move_to_element_and_click(selector=selector)

        await asyncio.sleep(random.uniform(1, 4))

        selector = ".vertical-align-middle.artdeco-pill.artdeco-pill--slate.artdeco-pill--3.artdeco-pill--choice.ember-view" ## Non lus
        button = await self.page.locator(selector=selector).all()
        for s in button:
            if 'Non lus' in await s.text_content():
                selector = s
                break

        await self.move_to_element_and_click(selector=selector)

        await asyncio.sleep(random.uniform(1, 2))

        selector = ".list-style-none.msg-conversations-container__conversations-list"
        container = self.page.locator(selector)

        truncate_elements = await container.locator(".truncate").all()

        # Extraire les textes des éléments 'truncate'
        liste_prospect = []
        for element in truncate_elements:
            text = await element.text_content()
            # Ajouter uniquement les textes uniques
            text=text.replace('\n', '')
            text = text.rstrip()
            text = text.lstrip()
            
            if text not in liste_prospect:
                liste_prospect.append(text)

        return liste_prospect    
    
    async def get_name_page(self) -> str:
        """
        Récupère une portion du titre de la page Playwright.
        :return: Le nom extrait du titre de la page.
        """
        titre = await self.page.title()  # Ajout de await ici
        t1 = 0
        if ')' in titre:
            t1 = titre.index(') ') + 2
        t2 = titre.index(' |')
        titre = titre[t1:t2]
        return titre
    
    async def get_div_centre_action(self):
        """
        Récupère l'élément parent du bouton contenant le texte 'Plus'.
        
        :return: L'élément parent ciblé ou None en cas d'erreur.
        """
        try:
            i = 0
            divs = await self.page.locator("//button[contains(@aria-label, 'Plus d’actions')]").all()
            for div in divs:
                text = await div.text_content()
                # Ajouter uniquement les textes uniques
                text=text.replace('\n', '')
                text = text.rstrip()
                text = text.lstrip()
                if text == 'Plus':  
                    if i == 1:
                        div_parent = div.locator('..')
                        div_cible = div_parent.locator('..')                                        
                        return div_cible
                    i+=1
        except Exception as e:
            logger.info(e)
            return None

    async def close_alert(self):
        try:
            logger.info("Début de la méthode")
            
            # Vérifie la présence du conteneur d'alerte
            alert = await self.page.query_selector('#artdeco-global-alert-container')
            if alert is None:
                logger.info("Aucune alerte détectée")
                return False
            
            logger.info("Alerte détectée, recherche du bouton 'Refuser'")
            
            # Sélectionne les boutons de l'alerte
            bouton_close_list = alert.locator('.artdeco-global-alert__action.artdeco-button.artdeco-button--inverse.artdeco-button--2.artdeco-button--primary.ember-view')
            count = await bouton_close_list.count()  # Ne pas oublier 'await' ici
            
            logger.info(f"Nombre de boutons trouvés : {count}")
            
            # Parcourt la liste des boutons pour trouver celui avec 'Refuser'
            for i in range(count):
                bouton_close = bouton_close_list.nth(i)
                bouton_text = await bouton_close.text_content()  # Ajout d'await ici
                logger.info(f"Bouton {i} : {bouton_text}")
                
                if 'Refuser' in bouton_text:
                    await bouton_close.click()  # Ajout d'await ici
                    logger.info("Bouton 'Refuser' cliqué")
                    return True
            
            logger.info("Bouton 'Refuser' non trouvé")
            return False
        except Exception as e:
            logger.error(f"Erreur rencontrée : {e}")  # Utilisation de logger.error pour signaler une exception
            return False

    
    def clean(self, text):
        text=text.replace('\n', '')
        text = text.rstrip()
        text = text.lstrip()

        return text

    async def connexion(self):
        """
        Envoi une demande de connexion a un Prospect
        """                       
        await asyncio.sleep(2)

        self.dernier_nom = await self.get_name_page()
        logger.info(self.dernier_nom)

        logger.info('debut')
        div = await self.get_div_centre_action()
        logger.info(await div.get_attribute('class'))
        if div is not None:
            children = div.locator(':scope > *')  
            count = await children.count()
            
            button = None
            for i in range(count):
                child = children.nth(i)
                text = self.clean(await child.text_content())
                logger.info(text)
                if text in ['Se connecter', 'Suivre', 'Accepter', 'En attente', 'Message']:
                    button = child
                    break
            
            if button is not None:
                button_text = self.clean(await button.text_content())
                if button_text == "Se connecter":
                    await self.move_to_element_and_click(button)
                    await asyncio.sleep(random.uniform(0.5, 2))

                    accept = await self.page.wait_for_selector(".artdeco-button.artdeco-button--2.artdeco-button--primary.ember-view.ml1", timeout=1000)

                    if accept is not None:
                        await asyncio.sleep(random.uniform(1, 3))
                        await self.move_to_element_and_click(accept)
                        return None
                    return None

                elif button_text == "Suivre":
                    ## trouver le bouton Plus
                    bouton_plus = None
                    for i in range(count):
                        child = children.nth(i)
                        text = self.clean(await child.text_content())
                        if "Plus" in text:
                            bouton_plus = child
                            break
                    await asyncio.sleep(random.uniform(0.5, 2))
                    await self.move_to_element_and_click(bouton_plus)

                    await asyncio.sleep(random.uniform(1, 3))

                    se_connecter = self.page.locator(f'//div[contains(@aria-label, "Invitez {self.dernier_nom} à rejoindre votre réseau")]').nth(1)
                    await self.move_to_element_and_click(se_connecter)

                    await asyncio.sleep(1, 3)

                    ## envoyer sans message 
                    accept = self.page.locator(".artdeco-button.artdeco-button--2.artdeco-button--primary.ember-view.ml1") ## Trouve le bouton de connexion
                    if accept is not None:
                        await self.move_to_element_and_click(accept)
                    return None

                elif button_text == "Accepter":
                    await self.move_to_element_and_click(button)
                    return None
                elif button_text == 'En attente':
                    return None
                else:
                    return None
            else:
                logger.info("bouton est none.")                
            return None
        return None


    async def envoiMessage(self, message : str):
        if self.close_alert():
            await asyncio.sleep(random.uniform(3, 7))
            div = await self.get_div_centre_action()
            children = div.locator(':scope > *')  
            count = await children.count()
            
            button = None
            for i in range(count):
                child = children.nth(i)
                text = self.clean(await child.text_content())
                logger.info(text)
                if text in ['Se connecter', 'Suivre', 'Accepter', 'En attente', 'Message']:
                    button = child
                    break

            if button is not None:
                await self.move_to_element_and_click(button)
                logger.info('bouton cliqué')

                await asyncio.sleep(random.uniform(1, 5))
                m = await self.page.locator(".msg-s-message-list__event.clearfix").all() ## message des gens 
                if m != None:
                    nom_conv = await self.get_name_page()
                    nb_participant = []
                    for message_element in m:
                        logger.info("message")
                        try:
                            sub_element = message_element.locator(".msg-s-message-group__profile-link.msg-s-message-group__name.t-14.t-black.t-bold.hoverable-link-text")
                            if self.clean(await sub_element.text_content()) not in nb_participant:
                                logger.info('ajout participant')
                                nb_participant.append(self.clean(await sub_element.text_content()))
                        except Exception as e:
                            logger.info(e)
                            sub_element = None  

                    if nom_conv in nb_participant:            
                        logger.info('message deja envoyé')
                        logger.info(nom_conv)
                        logger.info(nb_participant)

                        close_button = self.page.get_by_text('Fermer votre conversation avec')
                        await self.move_to_element_and_click(close_button)

                        await asyncio.sleep(random.uniform(3, 6))
                        return None
                    
                r = self.page.locator(".msg-form__msg-content-container.msg-form__message-texteditor.relative.flex-grow-1.display-flex")  

                # Vérifiez que l'élément est interactif
                if await r.is_enabled():
                    try:
                        # Simuler CTRL + A pour sélectionner le texte
                        await r.focus()
                        await self.page.keyboard.down('Control')
                        await self.page.keyboard.press('a')
                        await self.page.keyboard.up('Control')

                        # Simuler la touche Delete
                        await self.page.keyboard.press('Delete')
                        await self.page.wait_for_timeout(random.randint(1000, 2000))  # Attendre entre 1 et 2 secondes

                        # Envoyer un message
                        await self.type_like_human(message)
                        # await self.page.keyboard.type(message)  # Remplacez 'Message à envoyer' par le message réel

                    except Exception as e:
                        logger.info("Il y a eu une erreur lors de la saisie")
                        logger.info(f"Erreur : {e}")

                    try:
                        # Localiser le bouton d'envoi
                        button = self.page.locator('.msg-form__send-button.artdeco-button.artdeco-button--1')
                        await self.page.wait_for_timeout(random.randint(2000, 4000))  # Attendre entre 2 et 4 secondes
                        await self.move_to_element_and_click(button)
                        logger.info('Bouton cliqué')

                        # Localiser le bouton de fermeture
                        close_button = self.page.get_by_text('Fermer votre conversation avec')
                        await self.move_to_element_and_click(close_button)
                        logger.info('Bouton de fermeture cliqué')
                        
                        return None
                    except Exception as e:
                        logger.info("Il y a eu une erreur lors de l'appui du bouton")
                        logger.info(f"Erreur : {e}")
                else:
                    logger.info("L'élément n'est pas interactif.")
                    return None
                
    async def identifier_par_mail(self, identifiant, mdp):
        try:
            logger.info("lancement de la methode")
            logger.info(self.page)
            await self.page.screenshot(path="screenshot1.png", full_page=True)

            liens = await self.page.locator("a").all()
            for l in liens:
                logger.info("boucle l")
                try:
                    href = await l.get_attribute("href")
                    if href in "https://www.linkedin.com/login/fr":
                        locator = l
                        break
                except Exception as e:
                    logger.info(e)
            await self.page.screenshot(path="screenshot2.png", full_page=True)
            logger.info("debut")

            await self.move_to_element_and_click(locator)
            await asyncio.sleep(random.uniform(2, 4))

            nom_page = await self.get_name_page()     
            logger.info(nom_page)   
            ## deja dans le champs
            await self.type_like_human(identifiant)
            await self.page.screenshot(path='screen_suivi_1.png')  
            logger.info("1")

            await self.wait_natural()
            await self.press_tab_key() ## changement pour taper mdp
            await self.page.screenshot(path='screen_suivi_2.png')  
            logger.info("2")

            await self.wait_natural()

            await self.type_like_human(mdp)
            await self.page.screenshot(path='screen_suivi_3.png') 
            logger.info("3")

            await self.wait_natural()

            await self.press_enter_key()

            await self.page.screenshot(path='screen_suivi_4.png') 
            logger.info("4")

            await self.wait_natural()

            await self.page.screenshot(path='screen_suivi.png')  
            logger.info("screenshot reçu")

            logger.info(f"nom_page = {nom_page}, nom_page actuel = {await self.get_name_page()}")
            if nom_page == await self.get_name_page():
                logger.info("le mot de passe est éroné")
                return False

            return True
        except Exception as e:
            logger.info(f"erreur : {e}")
    
    async def taper_code_identification(self, code):
        await self.type_like_human(code)
        await self.wait_natural()
        await self.press_enter_key()
            
    async def is_log(self):
        if await self.get_name_page() == "LinkedIn : s’identifier ou s’inscrire":
            return False
        return True 
    

    # logique d'execution
    async def login_execution(self, identifiant, mdp, lien):
        """
        execute le code de login
        """
        await self.start(lien=lien)
        logger.info("page bien chargé")

        await self.wait_natural()

        await self.identifier_par_mail(identifiant=identifiant, mdp=mdp)
        logger.info("identification bien fini, regarder code reçu")

        logger.info("phase 1 completé -> lancement du listener d'evenement")
        code = self.listen_on_canal()
        logger.info(f"code recupéré : {code}")

        await self.taper_code_identification(self, code=code)
        logger.info(f"execution fini, titre de la page : {self.get_name_page()}")

        await self.stop()
    

