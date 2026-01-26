import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Optional

class DataService:
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data" / "manual"
        self.cache = {}
    
    def load_manual_data(self, filename: str) -> Dict:
        """Manuel JSON dosyasını yükle"""
        if filename in self.cache:
            return self.cache[filename]
        
        filepath = self.data_dir / f"{filename}.json"
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.cache[filename] = data
                return data
        except FileNotFoundError:
            print(f"Warning: {filename}.json not found")
            return {}
    
    def get_price_for_date(self, filename: str, target_date: date) -> Optional[float]:
        """Belirli bir tarih için fiyat getir"""
        data = self.load_manual_data(filename)
        date_str = target_date.isoformat()
        
        if date_str in data:
            return float(data[date_str])
        
        # Eğer tam tarih yoksa, en yakın önceki tarihi bul
        available_dates = sorted([d for d in data.keys() if d <= date_str])
        
        if available_dates:
            return float(data[available_dates[-1]])
        
        return None
    
    def get_asset_prices(self, target_date: date) -> Dict[str, Optional[float]]:
        """Tüm varlıkların fiyatlarını getir"""
        return {
            "USD": self.get_price_for_date("usd", target_date),
            "EUR": self.get_price_for_date("eur", target_date),
            "GOLD": self.get_price_for_date("gold", target_date),
            "SILVER": self.get_price_for_date("silver", target_date),
            "BTC": self.get_crypto_price("bitcoin", target_date),
            "INTEREST": self.get_price_for_date("interest", target_date),
            "HOUSING": self.get_price_for_date("housing", target_date),
            "CAR_NEW": self.get_price_for_date("car_new", target_date),
            "CAR_USED": self.get_price_for_date("car_used", target_date)
        }
    
    def get_crypto_price(self, coin_id: str, target_date: date) -> Optional[float]:
        """Kripto fiyatını getir"""
        data = self.load_manual_data("crypto")
        date_str = target_date.isoformat()
        
        if coin_id in data and date_str in data[coin_id]:
            return float(data[coin_id][date_str])
        
        # En yakın tarihi bul
        if coin_id in data:
            available_dates = sorted([d for d in data[coin_id].keys() if d <= date_str])
            if available_dates:
                return float(data[coin_id][available_dates[-1]])
        
        return None
    
    def get_inflation_rate(self, year: int) -> float:
        """Yıllık enflasyon oranını getir"""
        data = self.load_manual_data("inflation")
        return float(data.get(str(year), 0))
    
    def get_cumulative_inflation(self, start_date: date, end_date: date) -> float:
        """İki tarih arası kümülatif enflasyon"""
        start_year = start_date.year
        end_year = end_date.year
        
        cumulative = 1.0
        for year in range(start_year, end_year + 1):
            rate = self.get_inflation_rate(year)
            cumulative *= (1 + rate / 100)
        
        return (cumulative - 1) * 100
