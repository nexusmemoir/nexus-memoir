const dataService = require('./dataService');

/**
 * Ana simülasyon fonksiyonu
 */
async function runSimulation(params) {
  const { startDate, amount, asset, endDate } = params;
  
  // Tarihleri parse et
  const start = new Date(startDate);
  const end = endDate ? new Date(endDate) : new Date();
  
  // Başlangıç ve bitiş fiyatları
  const startPrices = await dataService.getAssetPrices(start);
  const endPrices = await dataService.getAssetPrices(end);
  
  // Seçilen varlık hesaplaması
  const result = await calculateAsset(asset, amount, startPrices, endPrices, start, end);
  
  // Tüm alternatif senaryolar
  const alternatives = await calculateAllAlternatives(amount, startPrices, endPrices, start, end);
  
  // Enflasyon analizi
  const inflation = await dataService.getCumulativeInflation(startDate, end.toISOString().split('T')[0]);
  
  // Satın alma gücü karşılaştırması
  const purchasingPower = await calculatePurchasingPower(amount, startPrices, endPrices);
  
  return {
    selected: result,
    alternatives,
    inflation,
    purchasingPower,
    period: {
      start: startDate,
      end: end.toISOString().split('T')[0],
      days: Math.floor((end - start) / (1000 * 60 * 60 * 24))
    }
  };
}

/**
 * Tek bir varlık için hesaplama
 */
async function calculateAsset(asset, amount, startPrices, endPrices, startDate, endDate) {
  const assetKey = asset.toUpperCase();
  const startPrice = startPrices[assetKey];
  const endPrice = endPrices[assetKey];
  
  if (!startPrice || !endPrice) {
    throw new Error(`Varlık verisi bulunamadı: ${asset}`);
  }
  
  let quantity, currentValue;
  
  // Varlık tipine göre hesaplama
  switch (assetKey) {
    case 'USD':
    case 'EUR':
      quantity = amount / startPrice;
      currentValue = quantity * endPrice;
      break;
      
    case 'GOLD':
    case 'SILVER':
      quantity = amount / startPrice; // gram
      currentValue = quantity * endPrice;
      break;
      
    case 'BTC':
      const usdTryStart = startPrices.USD;
      const usdTryEnd = endPrices.USD;
      const btcPriceStart = startPrice * usdTryStart;
      const btcPriceEnd = endPrice * usdTryEnd;
      quantity = amount / btcPriceStart;
      currentValue = quantity * btcPriceEnd;
      break;
      
    case 'INTEREST':
      // Bileşik faiz hesabı
      const years = (endDate - startDate) / (1000 * 60 * 60 * 24 * 365);
      currentValue = amount * Math.pow(1 + startPrice / 100, years);
      quantity = null;
      break;
      
    case 'HOUSING':
      quantity = amount / startPrice; // m²
      currentValue = quantity * endPrice;
      break;
      
    case 'CAR_NEW':
    case 'CAR_USED':
      quantity = amount / startPrice; // araç sayısı
      currentValue = quantity * endPrice;
      break;
      
    default:
      currentValue = amount;
      quantity = null;
  }
  
  const nominalReturn = currentValue - amount;
  const nominalReturnPercent = (nominalReturn / amount) * 100;
  
  return {
    asset: assetKey,
    initialAmount: amount,
    quantity,
    currentValue,
    nominalReturn,
    nominalReturnPercent,
    startPrice,
    endPrice
  };
}

/**
 * Tüm alternatif senaryoları hesapla
 */
async function calculateAllAlternatives(amount, startPrices, endPrices, startDate, endDate) {
  const assets = ['USD', 'EUR', 'GOLD', 'SILVER', 'BTC', 'INTEREST', 'HOUSING', 'CAR_NEW'];
  const results = [];
  
  for (const asset of assets) {
    try {
      const result = await calculateAsset(asset, amount, startPrices, endPrices, startDate, endDate);
      results.push(result);
    } catch (error) {
      console.error(`Error calculating ${asset}:`, error.message);
    }
  }
  
  // En iyi ve en kötüye göre sırala
  results.sort((a, b) => b.nominalReturnPercent - a.nominalReturnPercent);
  
  return results;
}

/**
 * Satın alma gücü karşılaştırması
 */
async function calculatePurchasingPower(amount, startPrices, endPrices) {
  const examples = [];
  
  // Altın ile
  const goldGramStart = amount / startPrices.GOLD;
  const goldGramEnd = amount / endPrices.GOLD;
  examples.push({
    item: 'Altın',
    unit: 'gram',
    then: Math.round(goldGramStart * 10) / 10,
    now: Math.round(goldGramEnd * 10) / 10,
    change: Math.round(((goldGramEnd - goldGramStart) / goldGramStart) * 100)
  });
  
  // Dolar ile
  const usdStart = amount / startPrices.USD;
  const usdEnd = amount / endPrices.USD;
  examples.push({
    item: 'Dolar',
    unit: 'USD',
    then: Math.round(usdStart * 100) / 100,
    now: Math.round(usdEnd * 100) / 100,
    change: Math.round(((usdEnd - usdStart) / usdStart) * 100)
  });
  
  // Konut m² ile
  if (startPrices.HOUSING && endPrices.HOUSING) {
    const housingStart = amount / startPrices.HOUSING;
    const housingEnd = amount / endPrices.HOUSING;
    examples.push({
      item: 'Konut',
      unit: 'm²',
      then: Math.round(housingStart * 10) / 10,
      now: Math.round(housingEnd * 10) / 10,
      change: Math.round(((housingEnd - housingStart) / housingStart) * 100)
    });
  }
  
  return examples;
}

/**
 * Reel getiri hesapla (enflasyon ayarlı)
 */
function calculateRealReturn(nominalReturn, inflation) {
  // Fisher denklemi: (1 + nominal) / (1 + enflasyon) - 1
  return ((1 + nominalReturn / 100) / (1 + inflation / 100) - 1) * 100;
}

/**
 * Tarihsel veri serisi oluştur (grafik için)
 */
async function generateTimeSeries(startDate, endDate, asset, amount) {
  const series = [];
  const start = new Date(startDate);
  const end = new Date(endDate);
  
  // Aylık data points (maksimum 60 ay)
  const totalMonths = (end.getFullYear() - start.getFullYear()) * 12 + (end.getMonth() - start.getMonth());
  const step = Math.max(1, Math.floor(totalMonths / 60));
  
  let current = new Date(start);
  while (current <= end) {
    try {
      const prices = await dataService.getAssetPrices(current);
      const result = await calculateAsset(asset, amount, 
        await dataService.getAssetPrices(start), 
        prices, 
        start, 
        current
      );
      
      series.push({
        date: current.toISOString().split('T')[0],
        value: result.currentValue
      });
      
      current.setMonth(current.getMonth() + step);
    } catch (error) {
      console.error('Time series error:', error.message);
    }
  }
  
  return series;
}

module.exports = {
  runSimulation,
  calculateAsset,
  calculateAllAlternatives,
  calculatePurchasingPower,
  calculateRealReturn,
  generateTimeSeries
};
