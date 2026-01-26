import os
from openai import OpenAI
from typing import Dict, Optional

class LLMService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Warning: OPENAI_API_KEY not found")
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key)
    
    def get_asset_name(self, asset_code: str) -> str:
        """Varlık kodunu Türkçe isme çevir"""
        names = {
            "USD": "Dolar",
            "EUR": "Euro",
            "GOLD": "Altın",
            "SILVER": "Gümüş",
            "BTC": "Bitcoin",
            "INTEREST": "Faiz",
            "HOUSING": "Konut (m²)",
            "CAR_NEW": "Sıfır Araç",
            "CAR_USED": "İkinci El Araç"
        }
        return names.get(asset_code, asset_code)
    
    def analyze_simulation(self, simulation_data: Dict) -> Optional[Dict]:
        """Simülasyon sonuçlarını LLM ile analiz et"""
        
        if not self.client:
            return self._generate_fallback_analysis(simulation_data)
        
        selected = simulation_data["selected"]
        alternatives = simulation_data["alternatives"]
        inflation = simulation_data["inflation"]
        purchasing_power = simulation_data["purchasingPower"]
        period = simulation_data["period"]
        
        best = alternatives[0]
        worst = alternatives[-1]
        
        # Prompt oluştur
        prompt = f"""Sen bir finansal analiz asistanısın. Türkiye'deki bir kullanıcı için geçmiş veri simülasyonu yaptı. Sonuçları sade, anlaşılır ve duygusal etkisi olan bir dille açıkla.

**Simülasyon Detayları:**
- Tarih aralığı: {period['start']} → {period['end']} ({period['days']} gün)
- Başlangıç tutarı: {selected['initialAmount']:,.0f} TL
- Seçilen varlık: {self.get_asset_name(selected['asset'])}

**Sonuç:**
- Bugünkü değer: {selected['currentValue']:,.0f} TL
- Nominal getiri: %{selected['nominalReturnPercent']:.2f}
- Kümülatif enflasyon: %{inflation:.2f}

**En İyi Alternatif:**
- {self.get_asset_name(best['asset'])}: {best['currentValue']:,.0f} TL (%{best['nominalReturnPercent']:.2f})

**En Kötü Alternatif:**
- {self.get_asset_name(worst['asset'])}: {worst['currentValue']:,.0f} TL (%{worst['nominalReturnPercent']:.2f})

**Satın Alma Gücü:**
{chr(10).join([f"- {p['item']}: O gün {p['then']} {p['unit']}, bugün {p['now']} {p['unit']} ({'+' if p['change'] > 0 else ''}{p['change']}%)" for p in purchasing_power])}

**Görevin:**
1. Kullanıcının kararını değerlendir (başarılı mı, fırsat mı kaçırdı?)
2. Enflasyonun etkisini vurgula (nominal vs reel)
3. Kaçırılan fırsatı somut rakamlarla göster
4. Satın alma gücündeki değişimi açıkla
5. Duygusal ama gerçekçi bir ton kullan
6. 3-4 paragraf, maksimum 250 kelime

**Önemli:**
- "Yatırım tavsiyesi" verme
- "Gelecekte ne olur" deme
- Sadece geçmiş verilerden bahset
- Türkçe yaz, samimi ol
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "Sen Türkiye ekonomisini iyi bilen, empatik ve açıklayıcı bir finansal analiz asistanısın. Karmaşık verileri sade dille anlatırsın."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            analysis_text = response.choices[0].message.content
            
            return {
                "text": analysis_text,
                "tokens": response.usage.total_tokens,
                "model": response.model
            }
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return self._generate_fallback_analysis(simulation_data)
    
    def _generate_fallback_analysis(self, simulation_data: Dict) -> Dict:
        """LLM olmadan basit analiz"""
        
        selected = simulation_data["selected"]
        alternatives = simulation_data["alternatives"]
        inflation = simulation_data["inflation"]
        period = simulation_data["period"]
        
        best = alternatives[0]
        
        real_return = ((1 + selected["nominalReturnPercent"] / 100) / (1 + inflation / 100) - 1) * 100
        opportunity_cost = best["currentValue"] - selected["currentValue"]
        
        text = f"{period['days']} gün önce {selected['initialAmount']:,.0f} TL'nizi {self.get_asset_name(selected['asset'])} olarak değerlendirdiniz. "
        
        if selected["nominalReturnPercent"] > 0:
            text += f"Bugün bu para {selected['currentValue']:,.0f} TL'ye ulaştı, yani %{selected['nominalReturnPercent']:.1f} nominal kazanç.\n\n"
        else:
            text += f"Ancak bugün değeri {selected['currentValue']:,.0f} TL'ye düştü, yani %{abs(selected['nominalReturnPercent']):.1f} kayıp.\n\n"
        
        text += f"Bu dönemde enflasyon %{inflation:.1f} oldu. Yani reel getiri aslında %{real_return:.1f}. "
        
        if real_return < 0:
            text += "Nominal olarak kazandınız ama satın alma gücünüz azaldı.\n\n"
        else:
            text += "Hem nominal hem de reel olarak kazandınız.\n\n"
        
        if opportunity_cost > 0:
            text += f"Aynı dönemde {self.get_asset_name(best['asset'])} tercih etseydiniz {best['currentValue']:,.0f} TL'niz olurdu. "
            text += f"Yani {opportunity_cost:,.0f} TL fırsat maliyeti var."
        else:
            text += "Tebrikler! En iyi seçeneği tercih etmişsiniz."
        
        return {
            "text": text,
            "tokens": 0,
            "model": "fallback"
        }
    
    def generate_share_text(self, simulation_data: Dict) -> str:
        """Sosyal medya paylaşım metni"""
        
        selected = simulation_data["selected"]
        alternatives = simulation_data["alternatives"]
        period = simulation_data["period"]
        
        best = alternatives[0]
        
        text = f"{period['start']} tarihinde {selected['initialAmount']:,.0f} TL {self.get_asset_name(selected['asset'])} alsaydım bugün {selected['currentValue']:,.0f} TL olurdu. En iyi seçenek {self.get_asset_name(best['asset'])} olurdu: {best['currentValue']:,.0f} TL! #KeşkeHesap"
        
        return text
