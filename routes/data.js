const express = require('express');
const router = express.Router();
const dataService = require('../services/dataService');

/**
 * GET /api/data/assets
 * Tüm varlıkların listesi ve metadata'sı
 */
router.get('/assets', (req, res) => {
  const assets = [
    {
      code: 'USD',
      name: 'Dolar',
      category: 'Döviz',
      icon: '💵',
      description: 'ABD Doları / Türk Lirası',
      unit: 'USD'
    },
    {
      code: 'EUR',
      name: 'Euro',
      category: 'Döviz',
      icon: '💶',
      description: 'Euro / Türk Lirası',
      unit: 'EUR'
    },
    {
      code: 'GOLD',
      name: 'Altın',
      category: '귀Metal',
      icon: '🪙',
      description: 'Gram altın (TL)',
      unit: 'gram'
    },
    {
      code: 'SILVER',
      name: 'Gümüş',
      category: '귀Metal',
      icon: '⚪',
      description: 'Gram gümüş (TL)',
      unit: 'gram'
    },
    {
      code: 'BTC',
      name: 'Bitcoin',
      category: 'Kripto',
      icon: '₿',
      description: 'Bitcoin (USD → TL)',
      unit: 'BTC'
    },
    {
      code: 'INTEREST',
      name: 'Faiz',
      category: 'Birikim',
      icon: '🏦',
      description: 'Ortalama mevduat faizi',
      unit: '%'
    },
    {
      code: 'HOUSING',
      name: 'Konut',
      category: 'Gayrimenkul',
      icon: '🏠',
      description: 'Konut m² fiyatı (İstanbul ort.)',
      unit: 'm²'
    },
    {
      code: 'CAR_NEW',
      name: 'Sıfır Araç',
      category: 'Otomotiv',
      icon: '🚗',
      description: 'Örnek: Orta segment sedan',
      unit: 'araç'
    },
    {
      code: 'CAR_USED',
      name: 'İkinci El Araç',
      category: 'Otomotiv',
      icon: '🚙',
      description: '5 yaşında ortalama araç',
      unit: 'araç'
    }
  ];
  
  res.json({ success: true, assets });
});

/**
 * GET /api/data/prices/:date
 * Belirli bir tarihteki tüm varlık fiyatları
 */
router.get('/prices/:date', async (req, res) => {
  try {
    const { date } = req.params;
    const dateObj = new Date(date);
    
    if (isNaN(dateObj.getTime())) {
      return res.status(400).json({ error: 'Geçersiz tarih formatı' });
    }
    
    const prices = await dataService.getAssetPrices(dateObj);
    
    res.json({ success: true, date, prices });
    
  } catch (error) {
    console.error('Prices error:', error);
    res.status(500).json({ error: 'Fiyatlar çekilemedi', message: error.message });
  }
});

/**
 * GET /api/data/inflation/:year
 * Belirli bir yılın enflasyon oranı
 */
router.get('/inflation/:year', async (req, res) => {
  try {
    const { year } = req.params;
    const yearNum = parseInt(year);
    
    if (isNaN(yearNum) || yearNum < 2000 || yearNum > new Date().getFullYear()) {
      return res.status(400).json({ error: 'Geçersiz yıl' });
    }
    
    const rate = await dataService.getInflationRate(yearNum);
    
    res.json({ success: true, year: yearNum, inflationRate: rate });
    
  } catch (error) {
    res.status(500).json({ error: 'Enflasyon verisi alınamadı' });
  }
});

/**
 * GET /api/data/date-range
 * Veri setinin kapsadığı tarih aralığı
 */
router.get('/date-range', (req, res) => {
  // MVP için sabit değerler
  const range = {
    minDate: '2010-01-01',
    maxDate: new Date().toISOString().split('T')[0],
    availableYears: Array.from(
      { length: new Date().getFullYear() - 2010 + 1 },
      (_, i) => 2010 + i
    )
  };
  
  res.json({ success: true, range });
});

/**
 * POST /api/data/validate
 * Kullanıcı girdilerini doğrula
 */
router.post('/validate', async (req, res) => {
  try {
    const { startDate, amount, asset } = req.body;
    const errors = [];
    
    // Tarih kontrolü
    const start = new Date(startDate);
    const now = new Date();
    
    if (isNaN(start.getTime())) {
      errors.push('Geçersiz tarih formatı');
    } else if (start > now) {
      errors.push('Gelecek tarih seçilemez');
    } else if (start < new Date('2010-01-01')) {
      errors.push('2010 öncesi veri mevcut değil');
    }
    
    // Tutar kontrolü
    if (!amount || amount <= 0) {
      errors.push('Tutar pozitif bir sayı olmalı');
    } else if (amount < 100) {
      errors.push('Minimum tutar: 100 TL');
    } else if (amount > 1000000000) {
      errors.push('Maksimum tutar: 1 milyar TL');
    }
    
    // Varlık kontrolü
    const validAssets = ['USD', 'EUR', 'GOLD', 'SILVER', 'BTC', 'INTEREST', 'HOUSING', 'CAR_NEW', 'CAR_USED'];
    if (!asset || !validAssets.includes(asset.toUpperCase())) {
      errors.push('Geçersiz varlık seçimi');
    }
    
    if (errors.length > 0) {
      return res.status(400).json({ valid: false, errors });
    }
    
    res.json({ valid: true, message: 'Tüm parametreler geçerli' });
    
  } catch (error) {
    res.status(500).json({ error: 'Doğrulama hatası' });
  }
});

module.exports = router;
