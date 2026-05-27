"""
CB_banks_selenium_parser.py
Парсер реестра кредитных организаций ЦБ РФ.

Источники по убыванию надёжности:
1) XML BIK https://www.cbr.ru/scripts/XML_bic.asp  ← основной (стабильный)
2) Статический HTML /banking_sector/credit/FullCoList/
3) Selenium на SPA /banking_sector/credit/
4) Демо-данные топ-20 банков
"""

from __future__ import annotations
import requests
from bs4 import BeautifulSoup
from parsers.base_parser import BaseParser

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


_BASE        = "https://www.cbr.ru"
_XML_BIC     = f"{_BASE}/scripts/XML_bic.asp"
_LIST_STATIC = f"{_BASE}/banking_sector/credit/FullCoList/"
_LIST_JS     = f"{_BASE}/banking_sector/credit/"
_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept-Language": "ru-RU,ru;q=0.9",
}

_DEMO_BANKS = [
    ("1481","СБЕРБАНК","Москва","20.06.1991","Универсальная"),
    ("1000","ВТБ","Санкт-Петербург","17.10.1990","Универсальная"),
    ("1326","АЛЬФА-БАНК","Москва","20.12.1990","Универсальная"),
    ("3349","ГАЗПРОМБАНК","Москва","13.11.1990","Универсальная"),
    ("3251","РОССЕЛЬХОЗБАНК","Москва","24.04.2000","Универсальная"),
    ("2272","МОСКОВСКИЙ КРЕДИТНЫЙ БАНК","Москва","05.08.1992","Универсальная"),
    ("3292","ОТКРЫТИЕ","Москва","15.12.1992","Универсальная"),
    ("3279","РАЙФФАЙЗЕНБАНК","Москва","10.06.1996","Универсальная"),
    ("3287","ЮНИКРЕДИТ БАНК","Москва","20.10.1989","Универсальная"),
    ("2748","РОСБАНК","Москва","02.03.1993","Универсальная"),
    ("3328","ТИНЬКОФФ БАНК","Москва","28.01.1994","Универсальная"),
    ("1942","СОВКОМБАНК","Кострома","01.11.1990","Универсальная"),
    ("1623","ПОЧТА БАНК","Москва","24.04.1990","Универсальная"),
    ("2275","РОСИНТЕРБАНК","Москва","30.09.1992","Базовая"),
    ("588","АК БАРС","Казань","29.11.1993","Универсальная"),
    ("436","УРАЛСИБ","Москва","23.11.1990","Универсальная"),
    ("1810","БАНК САНКТ-ПЕТЕРБУРГ","Санкт-Петербург","03.10.1990","Универсальная"),
    ("963","АБСОЛЮТ БАНК","Москва","22.04.1993","Универсальная"),
    ("459","БАНК ДОМ.РФ","Москва","30.11.1999","Универсальная"),
    ("3255","БАНК ЗЕНИТ","Москва","07.12.1994","Универсальная"),
]


class CBRBankSeleniumParser(BaseParser):
    def __init__(self, output_path="banks_cbr.csv", headless=True, use_selenium=False):
        super().__init__(output_path)
        self.headless = headless
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        self.driver = None

    # ---------- XML BIK ----------
    def fetch_xml(self) -> str | None:
        print(f"  [XML BIK] GET {_XML_BIC}")
        try:
            r = requests.get(_XML_BIC, headers=_HEADERS, timeout=20)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "windows-1251"
            return r.text
        except requests.RequestException as e:
            print(f"  [!] XML BIK недоступен: {e}")
            return None

    def parse_xml(self, xml_text: str) -> int:
        soup = BeautifulSoup(xml_text, "xml")
        added = 0
        for rec in soup.find_all("Record"):
            try:
                reg_number = (rec.get("IntCode") or "").strip()
                name = rec.NameP.get_text(strip=True) if rec.NameP else ""
                tnp  = rec.Tnp.get_text(strip=True)   if rec.Tnp   else ""
                nnp  = rec.Nnp.get_text(strip=True)   if rec.Nnp   else ""
                city = f"{tnp} {nnp}".strip()
                reg_date = rec.DateIn.get_text(strip=True) if rec.DateIn else ""
                if not name:
                    continue
                self.data.append({
                    "reg_number": reg_number, "name": name, "city": city,
                    "reg_date": reg_date, "license_type": "Универсальная",
                    "card_url": f"{_BASE}/banking_sector/credit/coinfo/?id={reg_number}" if reg_number else "",
                    "source": "cbr_xml_bic",
                })
                added += 1
            except Exception as e:
                print(f"  [!] строка XML: {e}")
        return added

    # ---------- Static HTML ----------
    def fetch_static(self) -> str | None:
        print(f"  [Static] GET {_LIST_STATIC}")
        try:
            r = requests.get(_LIST_STATIC, headers=_HEADERS, timeout=20)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
        except requests.RequestException as e:
            print(f"  [!] статика недоступна: {e}")
            return None

    def parse_static(self, html: str) -> int:
        soup = BeautifulSoup(html, "html.parser")
        table = (soup.find("table", class_="data")
                 or (soup.find("div", class_="table-wrapper") and
                     soup.find("div", class_="table-wrapper").find("table"))
                 or soup.find("table"))
        if not table:
            print("  [!] Таблица не найдена.")
            return 0
        added = 0
        rows = table.select("tbody tr") or table.find_all("tr")[1:]
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 2: continue
            reg_number = cols[0].get_text(strip=True)
            a_tag = cols[1].find("a")
            name = a_tag.get_text(strip=True) if a_tag else cols[1].get_text(strip=True)
            card_url = ""
            if a_tag and a_tag.get("href"):
                href = a_tag["href"]
                card_url = href if href.startswith("http") else f"{_BASE}{href}"
            city         = cols[2].get_text(strip=True) if len(cols) > 2 else ""
            reg_date     = cols[3].get_text(strip=True) if len(cols) > 3 else ""
            license_type = cols[4].get_text(strip=True) if len(cols) > 4 else "Универсальная"
            if not name: continue
            self.data.append({
                "reg_number": reg_number, "name": name, "city": city,
                "reg_date": reg_date, "license_type": license_type,
                "card_url": card_url, "source": "cbr_static",
            })
            added += 1
        return added

    # ---------- Selenium ----------
    def _init_driver(self):
        opts = Options()
        if self.headless: opts.add_argument("--headless=new")
        for a in ("--no-sandbox","--disable-dev-shm-usage",
                  "--window-size=1920,1080","--disable-gpu"):
            opts.add_argument(a)
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        self.driver = webdriver.Chrome(options=opts)
        self.driver.implicitly_wait(5)

    def fetch_selenium(self) -> bool:
        if not self.driver: self._init_driver()
        print(f"  [Selenium] GET {_LIST_JS}")
        self.driver.get(_LIST_JS)
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.table-wrapper table tbody tr")))
            return True
        except (TimeoutException, WebDriverException) as e:
            print(f"  [Selenium] {e}")
            return False

    def parse_selenium(self) -> int:
        rows = self.driver.find_elements(
            By.CSS_SELECTOR, "div.table-wrapper table tbody tr")
        added = 0
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) < 2: continue
            reg_number = cols[0].text.strip()
            a = cols[1].find_elements(By.TAG_NAME, "a")
            name = a[0].text.strip() if a else cols[1].text.strip()
            href = a[0].get_attribute("href") if a else ""
            self.data.append({
                "reg_number": reg_number, "name": name,
                "city": cols[2].text.strip() if len(cols)>2 else "",
                "reg_date": cols[3].text.strip() if len(cols)>3 else "",
                "license_type": cols[4].text.strip() if len(cols)>4 else "",
                "card_url": href or "", "source": "cbr_selenium",
            })
            added += 1
        return added

    # ---------- main ----------
    def run(self):
        added = 0
        try:
            xml = self.fetch_xml()
            if xml:
                added = self.parse_xml(xml); print(f"  XML BIK: +{added}")
            if added == 0:
                html = self.fetch_static()
                if html:
                    added = self.parse_static(html); print(f"  Static: +{added}")
            if added == 0 and self.use_selenium:
                if self.fetch_selenium():
                    added = self.parse_selenium(); print(f"  Selenium: +{added}")
        finally:
            if self.driver: self.driver.quit(); self.driver = None

        if added == 0:
            print("  ⚠ Все источники недоступны — использую демо-данные.")
            for reg,name,city,dt,lic in _DEMO_BANKS:
                self.data.append({"reg_number":reg,"name":name,"city":city,
                                  "reg_date":dt,"license_type":lic,
                                  "card_url":"","source":"demo"})

        df = self.to_dataframe()
        self.save(df)
        print(f"\n  ✓ Итого банков: {len(df)}")
        if not df.empty:
            print(df[["reg_number","name","city","license_type"]].head(5).to_string(index=False))
        return df


if __name__ == "__main__":
    CBRBankSeleniumParser("banks_cbr.csv").run()

