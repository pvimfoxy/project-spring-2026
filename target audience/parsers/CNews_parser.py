import time
import requests
from bs4 import BeautifulSoup
from parsers.base_parser import BaseParser


class CNewsMultiParser(BaseParser):
    """
    Парсер новостных лент трёх поддоменов CNews.
    Вёрстка: лента /news → блоки .allnews > .allnews_item,
    внутри каждого — .allnews_date + (.allnews_t > a).
    Пагинация: GET-параметр ?page=2, ?page=3 …
    """

    DEFAULT_SOURCES = [
        {
            "segment": "госструктуры",
            "base_url": "https://www.cnews.ru",
            "news_url": "https://gov.cnews.ru",
        },
        {
            "segment": "банки",
            "base_url": "https://www.cnews.ru",
            "news_url": "https://www.banks.cnews.ru",   
        },
        {
            "segment": "ритейлеры",
            "base_url": "https://www.cnews.ru",
            "news_url": "https://www.retail.cnews.ru",    
        },
    ]

    def __init__(self, output_path="cnews_segments.csv", max_pages=3, sources=None):
        super().__init__(output_path)
        self.max_pages = max_pages
        self.sources = sources if sources is not None else self.DEFAULT_SOURCES
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

    def fetch(self, news_url: str, page: int = 1) -> str | None:
        """
        Возвращает HTML страницы ленты.
        Пагинация CNews: ?page=N (страница 1 — без параметра).
        """
        params = {"page": page} if page > 1 else {}
        try:
            resp = self.session.get(news_url, params=params, timeout=10)
            resp.raise_for_status()
            # CNews отдаёт windows-1251 или utf-8 — requests определяет через chardet
            resp.encoding = resp.apparent_encoding
            return resp.text
        except requests.RequestException as e:
            print(f"  [!] Ошибка загрузки {news_url} (page={page}): {e}")
            return None

    def parse(self, html: str, segment: str, base_url: str) -> int:
        """
        Парсит HTML ленты /news.
        Реальная структура CNews:

            <div class="allnews">
              <div class="allnews_item">
                <span class="allnews_date">27.05 11:11</span>
                <span class="allnews_t">
                  <a href="/news/top/2025-05-27_zagolovok">Заголовок</a>
                </span>
              </div>
              ...
            </div>

        Возвращает количество добавленных записей.
        """
        soup = BeautifulSoup(html, "html.parser")
        added = 0

        # ── Основной контейнер ──────────────────────────────────────────
        container = soup.find("div", class_="allnews")

        if container:
            items = container.find_all("div", class_="allnews_item")
        else:
            # Запасной вариант: ищем по всему документу
            items = soup.find_all("div", class_="allnews_item")

        # ── Фолбэк для «Главной» и нестандартных разделов ───────────────
        # Главная страница: блоки вида <div class="news-item"> (новостные врезки)
        if not items:
            items = soup.select("div.news-item, div.news_item")

        # Совсем крайний случай — хватаем все ссылки из .allnews_t
        if not items:
            links = soup.select("span.allnews_t a")
            for a in links:
                href = self._abs_url(a.get("href", ""), base_url)
                title = a.get_text(strip=True)
                if title:
                    self.data.append({
                        "title":   title,
                        "url":     href,
                        "date":    "",
                        "snippet": "",
                        "segment": segment,
                        "source":  "cnews",
                    })
                    added += 1
            return added

        for item in items:

            # Заголовок + ссылка
            # Вариант 1: span.allnews_t > a  (лента /news)
            a_tag = item.select_one("span.allnews_t a")
            # Вариант 2: span.allnews_b > a  (иногда у «больших» анонсов)
            if not a_tag:
                a_tag = item.select_one("span.allnews_b a")
            # Вариант 3: любой первый <a> с непустым текстом
            if not a_tag:
                for a in item.find_all("a"):
                    if a.get_text(strip=True):
                        a_tag = a
                        break

            if not a_tag:
                continue

            title = a_tag.get_text(strip=True)
            href  = self._abs_url(a_tag.get("href", ""), base_url)

            # Дата
            # Вариант 1: span.allnews_date  → "27.05 11:11"
            date_tag = item.find("span", class_="allnews_date")
            # Вариант 2: span.date2  (используется в ряде разделов)
            if not date_tag:
                date_tag = item.find("span", class_="date2")
            # Вариант 3: span.date
            if not date_tag:
                date_tag = item.find("span", class_="date")
            # Вариант 4: <time datetime="...">
            if not date_tag:
                date_tag = item.find("time")

            date = date_tag.get_text(strip=True) if date_tag else ""

            # Сниппет (в ленте обычно отсутствует, но есть в разделах «top»)
            snippet_tag = (
                item.find("span", class_="allnews_a")
                or item.find("div",  class_="allnews_a")
                or item.find("span", class_="news-item__text")
                or item.find("div",  class_="news-item__text")
            )
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

            self.data.append({
                "title":   title,
                "url":     href,
                "date":    date,
                "snippet": snippet,
                "segment": segment,
                "source":  "cnews",
            })
            added += 1

        return added

    def _abs_url(self, href: str, base_url: str) -> str:
        """Приводит относительный href к абсолютному URL."""
        href = href.strip()
        if href.startswith("http"):
            return href
        if href.startswith("//"):
            return "https:" + href
        return base_url.rstrip("/") + "/" + href.lstrip("/")

    def _is_empty_page(self, html: str) -> bool:
        """
        Возвращает True, если страница не содержит блоков ленты
        (т.е. мы вышли за пределы пагинации).
        """
        soup = BeautifulSoup(html, "html.parser")
        return not (
            soup.find("div", class_="allnews_item")
            or soup.find("div", class_="news-item")
        )

    def run(self):
        for src in self.sources:
            segment  = src["segment"]
            base_url = src["base_url"]
            news_url = src["news_url"]
            print(f"\n>>> Раздел: {segment}  ({news_url})")

            for page in range(1, self.max_pages + 1):
                print(f"  Страница {page}...", end=" ", flush=True)

                html = self.fetch(news_url, page)
                if not html:
                    print("нет ответа — прерываем")
                    break

                if self._is_empty_page(html):
                    print("пустая страница — достигнут конец ленты")
                    break

                added = self.parse(html, segment, base_url)
                print(f"добавлено {added} новостей")

                time.sleep(2)   # уважаем сервер

        df = self.to_dataframe()
        self.save(df)
        return df


if __name__ == "__main__":
    parser = CNewsMultiParser(max_pages=2)
    df = parser.run()
    print(f"\nИтого собрано: {len(df)} статей")
    print(df["segment"].value_counts().to_string())

