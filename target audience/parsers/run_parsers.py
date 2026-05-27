"""
run_parsers.py
Запускает оба парсера и сохраняет результаты в папку data/.

Использование:
    python run_parsers.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parsers.CNews_parser import CNewsMultiParser
from parsers.CB_banks_selenium_parser import CBRBankSeleniumParser


def run():
    os.makedirs("data", exist_ok=True)

    # 1. Новости CNews 
    print("=" * 60)
    print("1/2  Парсинг новостей CNews (банки / ритейл / гос)...")
    print("=" * 60)

    cnews = CNewsMultiParser(
        output_path="data/cnews_segments.csv",
        max_pages=3,
    )
    df_news = cnews.run()
    print(f"\n Новостей собрано: {len(df_news)}")
    if not df_news.empty:
        print(df_news["segment"].value_counts().to_string())

    # 2. Банки ЦБ РФ 
    print("\n" + "=" * 60)
    print("2/2  Парсинг реестра банков (ЦБ РФ)...")
    print("=" * 60)

    cbr = CBRBankSeleniumParser(
        output_path="data/banks_cbr.csv",
        use_selenium=False,   # быстрый режим без Selenium
    )
    df_banks = cbr.run()
    print(f"\n✓ Банков собрано: {len(df_banks)}")

    print("\n Готово. Запустите dashboard.py")
    return df_news, df_banks


if __name__ == "__main__":
    run()
