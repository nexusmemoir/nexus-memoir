const axios = require('axios');
const NodeCache = require('node-cache');
const fs = require('fs').promises;
const path = require('path');

// Cache: geçmiş veriler sonsuza kadar, bugün 1 saat
const cache = new NodeCache({ stdTTL: 3600, checkperiod: 600 });

// Manuel veri yolu
const DATA_DIR = path.join(__dirname, '../data/manual');

/**
 * TCMB EVDS API'den veri çek
 */
async function fetchTCMB(series, startDate, endDate) {
  const cacheKey = `tcmb_${series}_${startDate}_${endDate}`;
  
  // Cache kontrol
  const cached = cache.get(cacheKey);
  if (cached) return cached;
  
  try {
    // TCMB EVDS API (ücretsiz, kayıt gerekli ama opsiyonel)
    const url = `https://evds2.tcmb.gov.tr/service/evds/`;
    const params = {
      series: series,
      startDate: startDate.replace(/-/g, ''),
      endDate: endDate.replace(/-/g, ''),
      type: 'json'
    };
    
    if (process.env.TCMB_API_KEY) {
      params.key = process.env.TCMB_API_KEY;
    }
    
    const response = await axios.get(url, { params, timeout: 10000 });
    const data = response.data.items || [];
    
    cache.set(cacheKey, data);
    return data;
  } catch (error) {
    console.error('TCMB API error:', error.message);
    // Fallback: manuel veri kullan
    return await loadManualData('tcmb', startDate, endDate);
  }
}

/**
 * CoinGecko API'den kripto fiyatı çek
 */
async function fetchCrypto(coinId, date) {
  const cacheKey = `crypto_${coinId}_${date}`;
  
  const cached = cache.get(cacheKey);
  if (cached) return cached;
  
  try {
    // CoinGecko historical data (free)
    const url = `https://api.coingecko.com/api/v3/coins/${coinId}/history`;
    const formattedDate = date.split('-').reverse().join('-'); // DD-MM-YYYY
    
    const response = await axios.get(url, {
      params: { date: formattedDate },
      timeout: 10000
    });
    
    const price = response.data.market_data?.current_price?.usd || null;
    cache.set(cacheKey, price);
    return price;
  } catch (error) {
    console.error('CoinGecko API error:', error.message);
    return await loadManualData('crypto', coinId, date);
  }
}

/**
 * Manuel veriyi yükle (CSV/JSON)
 */
async function loadManualData(type, ...params) {
  try {
    const filePath = path.join(DATA_DIR, `${type}.json`);
    const content = await fs.readFile(filePath, 'utf8');
    const data = JSON.parse(content);
    
    // Parametrelere göre filtreleme (basit örnek)
    if (type === 'crypto') {
      const [coinId, date] = params;
      return data[coinId]?.[date] || null;
    }
    
    return data;
  } catch (error) {
    console.error('Manual data load error:', error.message);
    return null;
  }
}

/**
 * Tüm varlıkların fiyatlarını getir
 */
async function getAssetPrices(date) {
  const dateStr = date.toISOString().split('T')[0];
  const today = new Date().toISOString().split('T')[0];
  
  const cacheKey = `all_prices_${dateStr}`;
  const cached = cache.get(cacheKey);
  if (cached && dateStr !== today) {
    return cached; // Geçmiş veriler cache'den
  }
  
  try {
    // Paralel API çağrıları
    const [usd, eur, gold, bitcoin] = await Promise.all([
      getUSDPrice(dateStr),
      getEURPrice(dateStr),
      getGoldPrice(dateStr),
      getBitcoinPrice(dateStr)
    ]);
    
    const prices = {
      date: dateStr,
      USD: usd,
      EUR: eur,
      GOLD: gold,
      BTC: bitcoin,
      SILVER: await getSilverPrice(dateStr),
      INTEREST: await getInterestRate(dateStr),
      HOUSING: await getHousingPrice(dateStr),
      CAR_NEW: await getCarPrice(dateStr, 'new'),
      CAR_USED: await getCarPrice(dateStr, 'used')
    };
    
    // Cache'e kaydet (geçmiş veriler sonsuza kadar)
    const ttl = dateStr === today ? 3600 : 0;
    cache.set(cacheKey, prices, ttl);
    
    return prices;
  } catch (error) {
    console.error('getAssetPrices error:', error);
    throw new Error('Veri çekilemedi');
  }
}

/**
 * USD/TRY kuru
 */
async function getUSDPrice(date) {
  try {
    // TCMB EVDS serisi: TP.DK.USD.A (USD Alış)
    const data = await fetchTCMB('TP.DK.USD.A', date, date);
    return data[0]?.TP_DK_USD_A || await loadManualData('usd', date);
  } catch (error) {
    return await loadManualData('usd', date);
  }
}

/**
 * EUR/TRY kuru
 */
async function getEURPrice(date) {
  try {
    const data = await fetchTCMB('TP.DK.EUR.A', date, date);
    return data[0]?.TP_DK_EUR_A || await loadManualData('eur', date);
  } catch (error) {
    return await loadManualData('eur', date);
  }
}

/**
 * Altın fiyatı (gram/TL)
 */
async function getGoldPrice(date) {
  try {
    const data = await fetchTCMB('TP.DK.USD.A.YTL', date, date);
    // TCMB'den ons/USD gelir, gram/TL'ye çevir
    const onsUSD = data[0]?.value || 1800;
    const usdTry = await getUSDPrice(date);
    return (onsUSD * usdTry) / 31.1035; // 1 ons = 31.1035 gram
  } catch (error) {
    return await loadManualData('gold', date);
  }
}

/**
 * Bitcoin fiyatı (USD)
 */
async function getBitcoinPrice(date) {
  return await fetchCrypto('bitcoin', date);
}

/**
 * Gümüş fiyatı (gram/TL)
 */
async function getSilverPrice(date) {
  return await loadManualData('silver', date);
}

/**
 * Ortalama mevduat faizi (yıllık %)
 */
async function getInterestRate(date) {
  try {
    const data = await fetchTCMB('TP.MRTEVD01', date, date);
    return data[0]?.TP_MRTEVD01 || await loadManualData('interest', date);
  } catch (error) {
    return await loadManualData('interest', date);
  }
}

/**
 * Konut fiyatı (m² başına TL - İstanbul ortalaması)
 */
async function getHousingPrice(date) {
  return await loadManualData('housing', date);
}

/**
 * Araç fiyatı (örnek model: Fiat Egea)
 */
async function getCarPrice(date, type = 'new') {
  return await loadManualData(`car_${type}`, date);
}

/**
 * Enflasyon oranı (yıllık %)
 */
async function getInflationRate(year) {
  const data = await loadManualData('inflation');
  return data[year] || 0;
}

/**
 * İki tarih arası kümülatif enflasyon
 */
async function getCumulativeInflation(startDate, endDate) {
  const startYear = new Date(startDate).getFullYear();
  const endYear = new Date(endDate).getFullYear();
  
  let cumulative = 1;
  for (let year = startYear; year <= endYear; year++) {
    const rate = await getInflationRate(year);
    cumulative *= (1 + rate / 100);
  }
  
  return (cumulative - 1) * 100; // % olarak dön
}

module.exports = {
  getAssetPrices,
  getUSDPrice,
  getEURPrice,
  getGoldPrice,
  getBitcoinPrice,
  getSilverPrice,
  getInterestRate,
  getHousingPrice,
  getCarPrice,
  getInflationRate,
  getCumulativeInflation
};
