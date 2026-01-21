import time
import psutil

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys


EMAIL    = 'email'
PASSWORD = 'haslo'
LOGIN_PAGE   = 'https://bilety.mhk.pl/uzytkownik/login.html'
# Strona „pusta” do refresh-spam
DUMMY_EMPTY_TICKETS_PAGE = 'https://bilety.mhk.pl/rezerwacja/termin.html?idg=0&idw=3&data=2025-09-10'
# Ewentualna strona testowa – możesz podmienić logicznie tak jak wcześniej
TICKETS_PAGE = 'https://bilety.mhk.pl/rezerwacja/termin.html?idg=0&idw=2&data=2025-11-14'

driver = webdriver.Chrome()

def login():
    driver.get(LOGIN_PAGE)
    wait = WebDriverWait(driver, timeout=15)

    email_input    = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#form_login_email.form-control')))[0]
    password_input = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#form_login_haslo.form-control')))[0]
    login_input    = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#form_login_submit.button')))[0]

    email_input.send_keys(EMAIL)
    password_input.send_keys(PASSWORD)
    login_input.click()

def open_tabs(url: str, n: int = 3):
    """Otwórz n nowych kart z podanym URL-em i zwróć listę uchwytów (handles)."""
    handles = [driver.current_window_handle]
    # Pierwsza karta: przejdź na URL
    driver.get(url)
    # Pozostałe karty: window.open
    for _ in range(n - 1):
        driver.execute_script(f"window.open('{url}', '_blank');")
        time.sleep(0.2)  # krótka przerwa, by Chrome załadował karty
    handles = driver.window_handles
    return handles

def switch_to(handle):
    driver.switch_to.window(handle)

def get_available_timeslot_buttons(wait: WebDriverWait):
    """Zwróć listę *dostępnych* przycisków timeslot (bez klasy button-dis)."""
    btns = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.timeslot-btn')))
    available = []
    for b in btns:
        cls = b.get_attribute('class') or ''
        if 'button-dis' not in cls:
            available.append(b)
    return available

def click_timeslot_index(available_btns, idx: int):
    """Kliknij w danej karcie przycisk o indeksie idx i wypisz jego tekst."""
    if len(available_btns) <= idx:
        raise IndexError(f'W tej karcie dostępnych jest tylko {len(available_btns)} przycisków, potrzebny indeks {idx}.')
    try:
        text = available_btns[idx].text.strip()
        print(f"[INFO] Klikam w przycisk: '{text}' (indeks {idx})")
        available_btns[idx].click()
        return True
    except (StaleElementReferenceException, NoSuchElementException):
        return False

def fill_ticket_form(wait: WebDriverWait):
    """Uzupełnij formularz biletów zgodnie z regułami."""
    tickets = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "divPozycjaCennika")))
    for ticket in tickets:
        label = ticket.find_element(By.CLASS_NAME, 'label').text.strip()
        count_field = ticket.find_element(By.CLASS_NAME, 'ilosc').find_element(By.CLASS_NAME, 'input-ilosc')
        # wyczyść pole, żeby uniknąć dopisywania
        count_field.send_keys(Keys.CONTROL, 'a')
        count_field.send_keys(Keys.DELETE)

        if label == 'Bilet grupowy normalny "Rynek Podziemny"':
            count_field.send_keys('25')
        elif label == 'Przewodnik zewnętrzny posiadający stosowny certyfikat':
            count_field.send_keys('1')
        # możesz dopisać kolejne warunki wg potrzeb

def run():
    login()

    # Otwórz 3 karty z tą samą stroną refreshowaną
    handles = open_tabs(DUMMY_EMPTY_TICKETS_PAGE, n=3)

    # Mapowanie: karta i -> ma kliknąć przycisk [i]
    target_index_for_tab = {handles[0]: 0, handles[1]: 1, handles[2]: 2}

    # Status, czy dana karta już kliknęła i przeszła do formularza
    done = {h: False for h in handles}

    # Ile razy próbujemy „rundami” odświeżać każdą kartę
    MAX_ROUNDS = 600  # ~600 iteracji; przy sleep 0.1 to ~60s aktywnego skanowania
    round_cnt = 0

    while not all(done.values()) and round_cnt < MAX_ROUNDS:
        round_cnt += 1

        for h in handles:
            if done[h]:
                continue  # ta karta już zrobiła klik i poszła dalej

            switch_to(h)
            # Szybki refresh tej karty
            driver.get(DUMMY_EMPTY_TICKETS_PAGE)
            # ⚠️ JEŚLI chcesz przełączać po X próbach na inną datę/URL, to zrób tu warunek

            # Krótki, indywidualny wait dla tej karty
            wait = WebDriverWait(driver, timeout=0.7)
            try:
                available = get_available_timeslot_buttons(wait)
                if not available:
                    # brak dostępnych timeslotów – lecimy dalej
                    continue

                idx_to_click = target_index_for_tab[h]
                ok = click_timeslot_index(available, idx_to_click)
                if ok:
                    # Udało się kliknąć w danej karcie — przejdź do formularza i uzupełnij
                    wait_form = WebDriverWait(driver, timeout=10)
                    fill_ticket_form(wait_form)
                    done[h] = True
                else:
                    # Spróbujemy w kolejnej rundzie (np. element zdążył zniknąć)
                    continue

            except TimeoutException:
                # w tej karcie nic nie ma (jeszcze) — kolejna runda
                continue
            except IndexError as e:
                # W tej karcie jest za mało dostępnych slotów, aby kliknąć dany indeks
                # Możesz to „zdegradować” do najbliższego dostępnego indeksu:
                # np. idx_to_click = min(idx_to_click, len(available)-1) i spróbować jeszcze raz
                # Na razie pomijamy i próbujemy w kolejnych rundach
                continue

        time.sleep(0.1)  # drobny oddech między rundami (round-robin)

    # (Opcjonalnie) po wszystkim trzymaj procesy dopóki użytkownik nie zamknie przeglądarki:
    webdriver_pid = driver.service.process.pid
    browser_processes = psutil.Process(webdriver_pid).children()
    print('Done. Zamknij okno przeglądarki, aby zakończyć bota.')
    for proc in browser_processes:
        try:
            proc.wait()
        except Exception:
            pass
    print('Exiting')

if __name__ == "__main__":
    run()
