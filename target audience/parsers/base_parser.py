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
    """Превращает сырые данные в структуру"""
    pass
