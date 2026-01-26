from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import os
from dotenv import load_dotenv
from datetime import datetime, date
import json

# Services import
from services.data_service import DataService
from services.calculation_service import CalculationService
from services.llm_service import LLMService

# Load environment
load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="WhatIf TR API",
    description="Alternatif Geçmiş Simülatörü Backend",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "*")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
data_service = DataService()
calculation_service = CalculationService(data_service)
llm_service = LLMService()

# Pydantic models
class SimulationRequest(BaseModel):
    startDate: str = Field(..., description="Başlangıç tarihi (YYYY-MM-DD)")
    amount: float = Field(..., gt=0, description="Tutar (TL)")
    asset: str = Field(..., description="Varlık kodu")
    endDate: Optional[str] = Field(None, description="Bitiş tarihi (opsiyonel)")
    includeLLM: bool = Field(True, description="LLM analizi dahil et")

class TimeSeriesRequest(BaseModel):
    startDate: str
    endDate: Optional[str] = None
    asset: str
    amount: float

# Health check
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    }

# Simulation endpoint
@app.post("/api/simulation/run")
async def run_simulation(request: SimulationRequest):
    try:
        # Validate dates
        start_date = datetime.strptime(request.startDate, "%Y-%m-%d").date()
        end_date = datetime.strptime(request.endDate, "%Y-%m-%d").date() if request.endDate else date.today()
        
        if start_date > end_date:
            raise HTTPException(400, "Başlangıç tarihi bitiş tarihinden sonra olamaz")
        
        if start_date > date.today():
            raise HTTPException(400, "Gelecek tarih seçilemez")
        
        if start_date.year < 2010:
            raise HTTPException(400, "2010 öncesi veri mevcut değil")
        
        # Run simulation
        simulation_result = calculation_service.run_simulation(
            start_date=start_date,
            end_date=end_date,
            amount=request.amount,
            asset=request.asset.upper()
        )
        
        # LLM analysis (optional)
        llm_analysis = None
        if request.includeLLM:
            llm_analysis = llm_service.analyze_simulation(simulation_result)
        
        return {
            "success": True,
            "simulation": simulation_result,
            "analysis": llm_analysis,
            "timestamp": datetime.now().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(400, f"Geçersiz tarih formatı: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"Simülasyon hatası: {str(e)}")

# Time series endpoint
@app.post("/api/simulation/time-series")
async def get_time_series(request: TimeSeriesRequest):
    try:
        start_date = datetime.strptime(request.startDate, "%Y-%m-%d").date()
        end_date = datetime.strptime(request.endDate, "%Y-%m-%d").date() if request.endDate else date.today()
        
        series = calculation_service.generate_time_series(
            start_date=start_date,
            end_date=end_date,
            asset=request.asset.upper(),
            amount=request.amount
        )
        
        return {
            "success": True,
            "series": series
        }
        
    except Exception as e:
        raise HTTPException(500, f"Veri çekilemedi: {str(e)}")

# Assets list
@app.get("/api/data/assets")
async def get_assets():
    assets = [
        {"code": "USD", "name": "Dolar", "category": "Döviz", "icon": "💵", "unit": "USD"},
        {"code": "EUR", "name": "Euro", "category": "Döviz", "icon": "💶", "unit": "EUR"},
        {"code": "GOLD", "name": "Altın", "category": "Değerli Metal", "icon": "🪙", "unit": "gram"},
        {"code": "SILVER", "name": "Gümüş", "category": "Değerli Metal", "icon": "⚪", "unit": "gram"},
        {"code": "BTC", "name": "Bitcoin", "category": "Kripto", "icon": "₿", "unit": "BTC"},
        {"code": "INTEREST", "name": "Faiz", "category": "Birikim", "icon": "🏦", "unit": "%"},
        {"code": "HOUSING", "name": "Konut", "category": "Gayrimenkul", "icon": "🏠", "unit": "m²"},
        {"code": "CAR_NEW", "name": "Sıfır Araç", "category": "Otomotiv", "icon": "🚗", "unit": "araç"},
        {"code": "CAR_USED", "name": "İkinci El Araç", "category": "Otomotiv", "icon": "🚙", "unit": "araç"}
    ]
    return {"success": True, "assets": assets}

# Examples
@app.get("/api/simulation/examples")
async def get_examples():
    examples = [
        {
            "id": 1,
            "title": "2020 başında Dolar alsaydım",
            "startDate": "2020-01-01",
            "amount": 10000,
            "asset": "USD",
            "description": "COVID öncesi dolar yatırımı"
        },
        {
            "id": 2,
            "title": "2017'de Bitcoin alsaydım",
            "startDate": "2017-01-01",
            "amount": 5000,
            "asset": "BTC",
            "description": "Kripto çılgınlığı öncesi"
        },
        {
            "id": 3,
            "title": "2015'te altın alsaydım",
            "startDate": "2015-01-01",
            "amount": 20000,
            "asset": "GOLD",
            "description": "Klasik güvenli liman"
        },
        {
            "id": 4,
            "title": "2010'da konut alsaydım",
            "startDate": "2010-01-01",
            "amount": 50000,
            "asset": "HOUSING",
            "description": "Gayrimenkul patlaması"
        }
    ]
    return {"success": True, "examples": examples}

# Prices endpoint
@app.get("/api/data/prices/{date}")
async def get_prices(date: str):
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        prices = data_service.get_asset_prices(date_obj)
        
        return {
            "success": True,
            "date": date,
            "prices": prices
        }
    except Exception as e:
        raise HTTPException(500, f"Fiyatlar çekilemedi: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
