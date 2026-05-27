"""
run_parsers.py — запускает оба парсера, сохраняет CSV в data/.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parsers.CNews_parser import CNewsMultiParser
from parsers.CB_banks_selenium_parser import CBRBankSeleniumParser


def run():
    os.makedirs("data", exist_ok=True)

    print("=" * 60)
    print("1/2  Парсинг новостей CNews (банки / ритейл / гос)")
    print("=" * 60)
    df_news = CNewsMultiParser(output_path="data/cnews_segments.csv", max_pages=3).run()
    print(f"\n  ✓ Новостей собрано: {len(df_news)}")
    if not df_news.empty:
        print(df_news["segment"].value_counts().to_string())

    print("\n" + "=" * 60)
    print("2/2  Парсинг реестра банков ЦБ РФ")
    print("=" * 60)
    df_banks = CBRBankSeleniumParser(output_path="data/banks_cbr.csv",
                                     use_selenium=False).run()
    print(f"\n  ✓ Банков собрано: {len(df_banks)}")
    print("\n>>> Готово. Запустите: python dashboard.py")
    return df_news, df_banks


if __name__ == "__main__":
    run()

