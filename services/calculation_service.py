from datetime import date, timedelta
from typing import Dict, List, Optional
from dateutil.relativedelta import relativedelta

class CalculationService:
    def __init__(self, data_service):
        self.data_service = data_service
    
    def run_simulation(self, start_date: date, end_date: date, amount: float, asset: str) -> Dict:
        """Ana simülasyon fonksiyonu"""
        
        # Başlangıç ve bitiş fiyatları
        start_prices = self.data_service.get_asset_prices(start_date)
        end_prices = self.data_service.get_asset_prices(end_date)
        
        # Seçilen varlık hesaplaması
        selected = self.calculate_asset(asset, amount, start_prices, end_prices, start_date, end_date)
        
        # Tüm alternatifler
        alternatives = self.calculate_all_alternatives(amount, start_prices, end_prices, start_date, end_date)
        
        # Enflasyon
        inflation = self.data_service.get_cumulative_inflation(start_date, end_date)
        
        # Satın alma gücü
        purchasing_power = self.calculate_purchasing_power(amount, start_prices, end_prices)
        
        # Dönem bilgisi
        days = (end_date - start_date).days
        
        return {
            "selected": selected,
            "alternatives": alternatives,
            "inflation": inflation,
            "purchasingPower": purchasing_power,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            }
        }
    
    def calculate_asset(self, asset: str, amount: float, start_prices: Dict, 
                       end_prices: Dict, start_date: date, end_date: date) -> Dict:
        """Tek varlık için hesaplama"""
        
        start_price = start_prices.get(asset)
        end_price = end_prices.get(asset)
        
        if not start_price or not end_price:
            raise ValueError(f"Varlık verisi bulunamadı: {asset}")
        
        quantity = None
        current_value = amount
        
        if asset in ["USD", "EUR", "GOLD", "SILVER"]:
            quantity = amount / start_price
            current_value = quantity * end_price
        
        elif asset == "BTC":
            # Bitcoin için USD/TRY kurunu da hesaba kat
            usd_start = start_prices.get("USD", 1)
            usd_end = end_prices.get("USD", 1)
            btc_price_start = start_price * usd_start
            btc_price_end = end_price * usd_end
            quantity = amount / btc_price_start
            current_value = quantity * btc_price_end
        
        elif asset == "INTEREST":
            # Bileşik faiz
            years = (end_date - start_date).days / 365.25
            current_value = amount * ((1 + start_price / 100) ** years)
        
        elif asset in ["HOUSING", "CAR_NEW", "CAR_USED"]:
            quantity = amount / start_price
            current_value = quantity * end_price
        
        nominal_return = current_value - amount
        nominal_return_percent = (nominal_return / amount) * 100
        
        return {
            "asset": asset,
            "initialAmount": amount,
            "quantity": quantity,
            "currentValue": current_value,
            "nominalReturn": nominal_return,
            "nominalReturnPercent": nominal_return_percent,
            "startPrice": start_price,
            "endPrice": end_price
        }
    
    def calculate_all_alternatives(self, amount: float, start_prices: Dict, 
                                  end_prices: Dict, start_date: date, end_date: date) -> List[Dict]:
        """Tüm alternatifleri hesapla"""
        
        assets = ["USD", "EUR", "GOLD", "SILVER", "BTC", "INTEREST", "HOUSING", "CAR_NEW"]
        results = []
        
        for asset in assets:
            try:
                result = self.calculate_asset(asset, amount, start_prices, end_prices, start_date, end_date)
                results.append(result)
            except Exception as e:
                print(f"Error calculating {asset}: {e}")
        
        # En iyiden en kötüye sırala
        results.sort(key=lambda x: x["nominalReturnPercent"], reverse=True)
        
        return results
    
    def calculate_purchasing_power(self, amount: float, start_prices: Dict, end_prices: Dict) -> List[Dict]:
        """Satın alma gücü karşılaştırması"""
        
        examples = []
        
        # Altın
        if start_prices.get("GOLD") and end_prices.get("GOLD"):
            gold_start = amount / start_prices["GOLD"]
            gold_end = amount / end_prices["GOLD"]
            examples.append({
                "item": "Altın",
                "unit": "gram",
                "then": round(gold_start, 1),
                "now": round(gold_end, 1),
                "change": round(((gold_end - gold_start) / gold_start) * 100, 1)
            })
        
        # Dolar
        if start_prices.get("USD") and end_prices.get("USD"):
            usd_start = amount / start_prices["USD"]
            usd_end = amount / end_prices["USD"]
            examples.append({
                "item": "Dolar",
                "unit": "USD",
                "then": round(usd_start, 2),
                "now": round(usd_end, 2),
                "change": round(((usd_end - usd_start) / usd_start) * 100, 1)
            })
        
        # Konut
        if start_prices.get("HOUSING") and end_prices.get("HOUSING"):
            housing_start = amount / start_prices["HOUSING"]
            housing_end = amount / end_prices["HOUSING"]
            examples.append({
                "item": "Konut",
                "unit": "m²",
                "then": round(housing_start, 1),
                "now": round(housing_end, 1),
                "change": round(((housing_end - housing_start) / housing_start) * 100, 1)
            })
        
        return examples
    
    def generate_time_series(self, start_date: date, end_date: date, 
                           asset: str, amount: float) -> List[Dict]:
        """Zaman serisi verisi oluştur"""
        
        series = []
        current = start_date
        
        # Aylık data points
        total_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
        step = max(1, total_months // 60)  # Maksimum 60 nokta
        
        while current <= end_date:
            try:
                start_prices = self.data_service.get_asset_prices(start_date)
                current_prices = self.data_service.get_asset_prices(current)
                
                result = self.calculate_asset(asset, amount, start_prices, current_prices, start_date, current)
                
                series.append({
                    "date": current.isoformat(),
                    "value": result["currentValue"]
                })
                
                current += relativedelta(months=step)
            except Exception as e:
                print(f"Time series error at {current}: {e}")
                current += relativedelta(months=step)
        
        return series
