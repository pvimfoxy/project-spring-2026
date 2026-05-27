from abc import ABC, abstractmethod
import pandas as pd

class BaseParser(ABC):
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.data = []

@abstractmethod
def fetch(self, *args, **kwargs):
    """Забирает данные из источника"""
    pass

@abstractmethod
def parse(self, raw_data):
    """Превращает данные в структуру"""
    pass

def to_dataframe(self) -> pd.DataFrame:
    return pd.DataFrame(self.data)

def save(self, df: pd.DataFrame = None):
     if df is None:
        df = self.to_dataframe()
     df.to_csv(self.output_path, index=False, encoding='utf-8-sig')
     print(f"Сохранено {len(df)} записей в {self.output_path}")
