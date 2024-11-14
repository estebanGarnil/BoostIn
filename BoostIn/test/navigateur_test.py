from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Configuration de Selenium avec Chrome
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Exécute Chrome en mode headless
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# Initialiser le navigateur
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    # Ouvrir la page Google
    driver.get("https://www.linkedin.com/home")

    # Trouver le champ de recherche par son nom
    s = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, '/html/body/main/section[1]/div/h1'))
    )

    # Imprimer un message si l'élément est trouvé
    print(s.text)

except Exception as e:
    print("Erreur:", e)

finally:
    # Fermer le navigateur
    driver.quit()
