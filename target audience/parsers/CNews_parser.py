"""
CNews_parser.py — парсер лент трёх поддоменов CNews:
    gov.cnews.ru / banks.cnews.ru / retail.cnews.ru.

При невозможности достучаться до сайта подкладывает демо-данные,
чтобы дашборд оставался работоспособным.
"""

from __future__ import annotations
import re, time, requests
from bs4 import BeautifulSoup
from parsers.base_parser import BaseParser


_DEMO_NEWS = [
    ("Банк ВТБ перенёс ядро АБС в новый ЦОД уровня Tier IV",
     "https://www.banks.cnews.ru/news/top/demo_vtb_tier4", "27.05 11:11", "банки"),
    ("Сбербанк инвестирует 80 млрд руб. в развитие собственных дата-центров",
     "https://www.banks.cnews.ru/news/top/demo_sber_dc", "26.05 16:00", "банки"),
    ("Газпромбанк выбрал коммерческий ЦОД для DR-площадки",
     "https://www.banks.cnews.ru/news/top/demo_gpb_dr", "25.05 09:30", "банки"),
    ("ЦБ ужесточил требования к отказоустойчивости IT-инфраструктуры банков",
     "https://www.banks.cnews.ru/news/top/demo_cbr_req", "24.05 12:00", "банки"),
    ("Альфа-Банк мигрирует процессинг в гибридное облако",
     "https://www.banks.cnews.ru/news/top/demo_alfa_cloud", "23.05 10:00", "банки"),
    ("X5 Retail Group построит распределённую сеть ЦОД для онлайн-заказов",
     "https://retail.cnews.ru/news/top/demo_x5_dc", "27.05 10:00", "ритейлеры"),
    ("Магнит перешёл на резервирование данных в коммерческом дата-центре",
     "https://retail.cnews.ru/news/top/demo_magnit_dc", "26.05 14:00", "ритейлеры"),
    ("Wildberries увеличил мощность ЦОД на 40% перед сезоном распродаж",
     "https://retail.cnews.ru/news/top/demo_wb_dc", "25.05 11:00", "ритейлеры"),
    ("Lenta.ru запустила собственную платформу аналитики на базе аренды стоек",
     "https://retail.cnews.ru/news/top/demo_lenta_dc", "24.05 09:00", "ритейлеры"),
    ("Ozon арендовал 200 стоек у внешнего оператора ЦОД",
     "https://retail.cnews.ru/news/top/demo_ozon_dc", "23.05 08:30", "ритейлеры"),
    ("Минцифры обновило требования к государственным ЦОД",
     "https://gov.cnews.ru/news/top/demo_mincifry_dc", "27.05 12:30", "госструктуры"),
    ("ФНС перенесла часть инфраструктуры в коммерческий ЦОД Tier IV",
     "https://gov.cnews.ru/news/top/demo_fns_tier4", "26.05 15:30", "госструктуры"),
    ("Госуслуги: запущен новый резервный дата-центр",
     "https://gov.cnews.ru/news/top/demo_gosuslugi_dr", "25.05 13:30", "госструктуры"),
    ("Регионы получат субсидии на размещение в защищённых ЦОД",
     "https://gov.cnews.ru/news/top/demo_subs_regions", "24.05 11:30", "госструктуры"),
    ("МВД консолидирует серверы в едином дата-центре",
     "https://gov.cnews.ru/news/top/demo_mvd_dc", "23.05 09:30", "госструктуры"),
]


class CNewsMultiParser(BaseParser):
    DEFAULT_SOURCES = [
        {"segment": "госструктуры", "news_url": "https://gov.cnews.ru/news"},
        {"segment": "банки",        "news_url": "https://www.banks.cnews.ru/news"},
        {"segment": "ритейлеры",    "news_url": "https://retail.cnews.ru/news"},
    ]

    def __init__(self, output_path="cnews_segments.csv", max_pages=3,
                 sources=None, sleep_sec: float = 1.5):
        super().__init__(output_path)
        self.max_pages = max_pages
        self.sources = sources if sources is not None else self.DEFAULT_SOURCES
        self.sleep_sec = sleep_sec
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/124.0.0.0 Safari/537.36"),
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

    def fetch(self, news_url: str, page: int = 1) -> str | None:
        params = {"page": page} if page > 1 else None
        try:
            resp = self.session.get(news_url, params=params, timeout=15)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            return resp.text
        except requests.RequestException as e:
            print(f"  [!] {news_url} (page={page}): {e}")
            return None

    def parse(self, html: str, segment: str) -> int:
        soup = BeautifulSoup(html, "html.parser")
        added = 0
        items = (soup.select("div.allnews div.allnews_item")
                 or soup.select("div.allnews_item")
                 or soup.select("div.news-item, div.news_item"))

        if items:
            for item in items:
                a = (item.select_one("span.allnews_t a")
                     or item.select_one("span.allnews_b a")
                     or item.find("a", href=True))
                if not a:
                    continue
                title = a.get_text(strip=True)
                href  = self._abs_url(a.get("href", ""))
                if not title or not href:
                    continue
                date_tag = (item.find("span", class_="allnews_date")
                            or item.find("span", class_="date2")
                            or item.find("span", class_="date")
                            or item.find("time"))
                date = date_tag.get_text(strip=True) if date_tag else ""
                snippet_tag = (item.find("span", class_="allnews_a")
                               or item.find("div", class_="allnews_a")
                               or item.find(class_=re.compile(r"news-item__text")))
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                self.data.append({
                    "title": title, "url": href, "date": date,
                    "snippet": snippet, "segment": segment, "source": "cnews",
                })
                added += 1
            return added

        # фолбэк: на странице нет блоков ленты — берём все «новостные» ссылки
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if "/news/" not in href:
                continue
            title = a.get_text(strip=True)
            if len(title) < 25:
                continue
            self.data.append({
                "title": title, "url": self._abs_url(href),
                "date": "", "snippet": "",
                "segment": segment, "source": "cnews_fallback",
            })
            added += 1
            if added >= 30:
                break
        return added

    @staticmethod
    def _abs_url(href: str) -> str:
        href = (href or "").strip()
        if href.startswith("http"):  return href
        if href.startswith("//"):    return "https:" + href
        if href.startswith("/"):     return "https://www.cnews.ru" + href
        return "https://www.cnews.ru/" + href

    def _is_empty(self, html: str) -> bool:
        soup = BeautifulSoup(html, "html.parser")
        return not soup.select_one("div.allnews_item, div.news-item, a[href*='/news/']")

    def run(self):
        for src in self.sources:
            segment, news_url = src["segment"], src["news_url"]
            print(f"\n>>> {segment.upper():<14}  {news_url}")
            for page in range(1, self.max_pages + 1):
                print(f"  стр. {page}…", end=" ", flush=True)
                html = self.fetch(news_url, page)
                if not html:
                    print("нет ответа"); break
                if self._is_empty(html):
                    print("пусто — конец ленты"); break
                n = self.parse(html, segment)
                print(f"+{n}")
                time.sleep(self.sleep_sec)

        seen, dedup = set(), []
        for row in self.data:
            if row["url"] in seen: continue
            seen.add(row["url"]); dedup.append(row)
        self.data = dedup

        if not self.data:
            print("\n  ⚠ Сайт недоступен — использую демо-данные.")
            for title, url, date, seg in _DEMO_NEWS:
                self.data.append({"title": title, "url": url, "date": date,
                                  "snippet": "", "segment": seg, "source": "demo"})

        df = self.to_dataframe()
        self.save(df)
        return df


if __name__ == "__main__":
    df = CNewsMultiParser(max_pages=2).run()
    print(f"\nИтого: {len(df)}")
    if not df.empty:
        print(df["segment"].value_counts().to_string())


