const OpenAI = require('openai');

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
});

/**
 * Simülasyon sonuçlarını LLM ile analiz et ve açıkla
 */
async function analyzeSimulation(simulationData) {
  const { selected, alternatives, inflation, purchasingPower, period } = simulationData;
  
  // En iyi ve en kötü alternatifleri bul
  const best = alternatives[0];
  const worst = alternatives[alternatives.length - 1];
  
  // Prompt oluştur
  const prompt = `Sen bir finansal analiz asistanısın. Türkiye'deki bir kullanıcı için geçmiş veri simülasyonu yaptı. Sonuçları sade, anlaşılır ve duygusal etkisi olan bir dille açıkla.

**Simülasyon Detayları:**
- Tarih aralığı: ${period.start} → ${period.end} (${period.days} gün)
- Başlangıç tutarı: ${selected.initialAmount.toLocaleString('tr-TR')} TL
- Seçilen varlık: ${getAssetName(selected.asset)}

**Sonuç:**
- Bugünkü değer: ${selected.currentValue.toLocaleString('tr-TR')} TL
- Nominal getiri: %${selected.nominalReturnPercent.toFixed(2)}
- Kümülatif enflasyon: %${inflation.toFixed(2)}

**En İyi Alternatif:**
- ${getAssetName(best.asset)}: ${best.currentValue.toLocaleString('tr-TR')} TL (%${best.nominalReturnPercent.toFixed(2)})

**En Kötü Alternatif:**
- ${getAssetName(worst.asset)}: ${worst.currentValue.toLocaleString('tr-TR')} TL (%${worst.nominalReturnPercent.toFixed(2)})

**Satın Alma Gücü:**
${purchasingPower.map(p => `- ${p.item}: O gün ${p.then} ${p.unit}, bugün ${p.now} ${p.unit} (${p.change > 0 ? '+' : ''}${p.change}%)`).join('\n')}

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
`;

  try {
    const completion = await openai.chat.completions.create({
      model: 'gpt-4-turbo-preview',
      messages: [
        {
          role: 'system',
          content: 'Sen Türkiye ekonomisini iyi bilen, empatik ve açıklayıcı bir finansal analiz asistanısın. Karmaşık verileri sade dille anlatırsın.'
        },
        {
          role: 'user',
          content: prompt
        }
      ],
      temperature: 0.7,
      max_tokens: 500
    });
    
    const analysis = completion.choices[0].message.content;
    
    return {
      text: analysis,
      tokens: completion.usage.total_tokens,
      model: completion.model
    };
  } catch (error) {
    console.error('OpenAI API error:', error.message);
    
    // Fallback: basit analiz
    return {
      text: generateFallbackAnalysis(simulationData),
      tokens: 0,
      model: 'fallback'
    };
  }
}

/**
 * LLM olmadan basit analiz (fallback)
 */
function generateFallbackAnalysis(simulationData) {
  const { selected, alternatives, inflation, period } = simulationData;
  const best = alternatives[0];
  
  const realReturn = ((1 + selected.nominalReturnPercent / 100) / (1 + inflation / 100) - 1) * 100;
  const opportunityCost = best.currentValue - selected.currentValue;
  
  let text = `${period.days} gün önce ${selected.initialAmount.toLocaleString('tr-TR')} TL'nizi ${getAssetName(selected.asset)} olarak değerlendirdiniz. `;
  
  if (selected.nominalReturnPercent > 0) {
    text += `Bugün bu para ${selected.currentValue.toLocaleString('tr-TR')} TL'ye ulaştı, yani %${selected.nominalReturnPercent.toFixed(1)} nominal kazanç.\n\n`;
  } else {
    text += `Ancak bugün değeri ${selected.currentValue.toLocaleString('tr-TR')} TL'ye düştü, yani %${Math.abs(selected.nominalReturnPercent).toFixed(1)} kayıp.\n\n`;
  }
  
  text += `Bu dönemde enflasyon %${inflation.toFixed(1)} oldu. Yani reel getiri aslında %${realReturn.toFixed(1)}. `;
  
  if (realReturn < 0) {
    text += `Nominal olarak kazandınız ama satın alma gücünüz azaldı.\n\n`;
  } else {
    text += `Hem nominal hem de reel olarak kazandınız.\n\n`;
  }
  
  if (opportunityCost > 0) {
    text += `Aynı dönemde ${getAssetName(best.asset)} tercih etseydiniz ${best.currentValue.toLocaleString('tr-TR')} TL'niz olurdu. `;
    text += `Yani ${opportunityCost.toLocaleString('tr-TR')} TL fırsat maliyeti var.`;
  } else {
    text += `Tebrikler! En iyi seçeneği tercih etmişsiniz.`;
  }
  
  return text;
}

/**
 * Varlık kodunu Türkçe isme çevir
 */
function getAssetName(assetCode) {
  const names = {
    'USD': 'Dolar',
    'EUR': 'Euro',
    'GOLD': 'Altın',
    'SILVER': 'Gümüş',
    'BTC': 'Bitcoin',
    'INTEREST': 'Faiz',
    'HOUSING': 'Konut (m²)',
    'CAR_NEW': 'Sıfır Araç',
    'CAR_USED': 'İkinci El Araç',
    'TRY': 'TL (Bankada)'
  };
  
  return names[assetCode] || assetCode;
}

/**
 * Sosyal medya paylaşımı için kısa özet oluştur
 */
async function generateShareText(simulationData) {
  const { selected, alternatives, period } = simulationData;
  const best = alternatives[0];
  
  const text = `${period.start} tarihinde ${selected.initialAmount.toLocaleString('tr-TR')} TL ${getAssetName(selected.asset)} alsaydım bugün ${selected.currentValue.toLocaleString('tr-TR')} TL olurdu. En iyi seçenek ${getAssetName(best.asset)} olurdu: ${best.currentValue.toLocaleString('tr-TR')} TL! #KeşkeHesap`;
  
  return text;
}

module.exports = {
  analyzeSimulation,
  generateShareText,
  getAssetName
};
