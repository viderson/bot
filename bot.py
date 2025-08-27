import time
import psutil

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys


EMAIL    = 'info@poland-service.com'
PASSWORD = 'mshAl561'
LOGIN_PAGE   = 'https://bilety.mhk.pl/uzytkownik/login.html'
TICKETS_PAGE = 'https://bilety.mhk.pl/rezerwacja/termin.html?idg=0&idw=2&data=2025-11-14'
DUMMY_EMPTY_TICKETS_PAGE = 'https://bilety.mhk.pl/rezerwacja/termin.html?idg=0&data=2025-11-24&idw=2&id_jezyka=0'

driver = webdriver.Chrome()

def login():
    # Open login page
    driver.get(LOGIN_PAGE)
    wait = WebDriverWait(driver, timeout=10)
    
    # Find mail, pass fields 
    email_input    = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#form_login_email.form-control')))[0]
    password_input = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#form_login_haslo.form-control')))[0]
    login_input    = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#form_login_submit.button')))[0]
    
    # Fill mail, pass fields 
    email_input.send_keys(EMAIL)
    password_input.send_keys(PASSWORD)
    
    # Click "Zaloguj" btn
    login_input.click()

login()




try_count = 0
refresh_page = DUMMY_EMPTY_TICKETS_PAGE
btns = None
found = False
while not found:
    driver.get(refresh_page)
    wait = WebDriverWait(driver, timeout=0.1)

    try:
        btns = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.timeslot-btn')))
    except TimeoutException:
        print('Couldn\'t find offers. Refreshing')
        try_count += 1

        if try_count == 10:     #test z przejsciem na inna strone
            refresh_page = TICKETS_PAGE
    else:
        found = True

btns_available = []
bts_locked     = []

for btn in btns:
    btn_class = btn.get_attribute('class')
    if 'button-dis' in btn_class:
        bts_locked.append(btn)
    else:
        btns_available.append(btn)


btns_available[0].click()

tickets = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "divPozycjaCennika")))
for ticket in tickets:
    label = ticket.find_element(By.CLASS_NAME, 'label').text.strip()
    price = ticket.find_element(By.CLASS_NAME, 'cena').text.strip()
    value = ticket.find_element(By.CLASS_NAME, 'wartosc').text.strip()

    count_field = ticket.find_element(By.CLASS_NAME, 'ilosc').find_element(By.CLASS_NAME, 'input-ilosc')
    if label == 'Bilet grupowy "Fabryka Schindlera"':
        count_field.send_keys('25')
    elif label == 'Przewodnik zewnętrzny posiadający stosowny certyfikat':
        count_field.send_keys('1')
    
    count = count_field.get_attribute('value')
    # print(label, price, value)
    # print(count)
    # print()

webdriver_pid = driver.service.process.pid
browser_processes = psutil.Process(webdriver_pid).children()
print('Work is done. Close Browser to exit bot uwu')
for proc in browser_processes:
    proc.wait()
print('Exiting')

# slot.text