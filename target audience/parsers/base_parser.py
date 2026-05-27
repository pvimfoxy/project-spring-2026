"""
base_parser.py
Базовый класс для всех парсеров проекта.

Хранит итоговый список словарей в self.data, умеет отдавать его
в виде pandas.DataFrame и сохранять в CSV (utf-8-sig — корректно
открывается в Excel).
"""

import os
import pandas as pd


class BaseParser:
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.data: list[dict] = []

    def fetch(self, *args, **kwargs):
        raise NotImplementedError("fetch() должен быть реализован в наследнике")

    def parse(self, *args, **kwargs):
        raise NotImplementedError("parse() должен быть реализован в наследнике")

    def run(self, *args, **kwargs):
        raise NotImplementedError("run() должен быть реализован в наследнике")

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.data)

    def save(self, df: pd.DataFrame | None = None) -> None:
        if df is None:
            df = self.to_dataframe()
        out_dir = os.path.dirname(self.output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        df.to_csv(self.output_path, index=False, encoding="utf-8-sig")
        print(f"  ✓ Сохранено {len(df)} записей → {self.output_path}")

