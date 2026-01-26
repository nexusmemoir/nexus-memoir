const express = require('express');
const router = express.Router();
const calculationService = require('../services/calculationService');
const llmService = require('../services/llmService');

/**
 * POST /api/simulation/run
 * Ana simülasyon endpoint'i
 */
router.post('/run', async (req, res) => {
  try {
    const { startDate, amount, asset, endDate, includeLLM } = req.body;
    
    // Validasyon
    if (!startDate || !amount || !asset) {
      return res.status(400).json({ 
        error: 'Eksik parametreler',
        required: ['startDate', 'amount', 'asset']
      });
    }
    
    if (amount <= 0) {
      return res.status(400).json({ error: 'Tutar pozitif olmalı' });
    }
    
    const start = new Date(startDate);
    const end = endDate ? new Date(endDate) : new Date();
    
    if (start > end) {
      return res.status(400).json({ error: 'Başlangıç tarihi bitiş tarihinden sonra olamaz' });
    }
    
    if (start > new Date()) {
      return res.status(400).json({ error: 'Gelecek tarih seçilemez' });
    }
    
    // Simülasyonu çalıştır
    const simulationResult = await calculationService.runSimulation({
      startDate,
      amount: parseFloat(amount),
      asset,
      endDate: end.toISOString().split('T')[0]
    });
    
    // LLM analizi (opsiyonel)
    let llmAnalysis = null;
    if (includeLLM !== false) {
      llmAnalysis = await llmService.analyzeSimulation(simulationResult);
    }
    
    // Sonucu döndür
    res.json({
      success: true,
      simulation: simulationResult,
      analysis: llmAnalysis,
      timestamp: new Date().toISOString()
    });
    
  } catch (error) {
    console.error('Simulation error:', error);
    res.status(500).json({ 
      error: 'Simülasyon hatası',
      message: error.message 
    });
  }
});

/**
 * POST /api/simulation/time-series
 * Grafik için zaman serisi verisi
 */
router.post('/time-series', async (req, res) => {
  try {
    const { startDate, endDate, asset, amount } = req.body;
    
    if (!startDate || !asset || !amount) {
      return res.status(400).json({ error: 'Eksik parametreler' });
    }
    
    const series = await calculationService.generateTimeSeries(
      startDate,
      endDate || new Date().toISOString().split('T')[0],
      asset,
      parseFloat(amount)
    );
    
    res.json({ success: true, series });
    
  } catch (error) {
    console.error('Time series error:', error);
    res.status(500).json({ error: 'Veri çekilemedi', message: error.message });
  }
});

/**
 * POST /api/simulation/share
 * Paylaşım metni oluştur
 */
router.post('/share', async (req, res) => {
  try {
    const { simulationData } = req.body;
    
    if (!simulationData) {
      return res.status(400).json({ error: 'Simülasyon verisi gerekli' });
    }
    
    const shareText = await llmService.generateShareText(simulationData);
    
    res.json({ success: true, shareText });
    
  } catch (error) {
    console.error('Share text error:', error);
    res.status(500).json({ error: 'Paylaşım metni oluşturulamadı' });
  }
});

/**
 * GET /api/simulation/examples
 * Örnek senaryolar
 */
router.get('/examples', async (req, res) => {
  try {
    const examples = [
      {
        id: 1,
        title: '2020 başında Dolar alsaydım',
        startDate: '2020-01-01',
        amount: 10000,
        asset: 'USD',
        description: 'COVID öncesi dolar yatırımı'
      },
      {
        id: 2,
        title: '2017\'de Bitcoin alsaydım',
        startDate: '2017-01-01',
        amount: 5000,
        asset: 'BTC',
        description: 'Kripto çılgınlığı öncesi'
      },
      {
        id: 3,
        title: '2015\'te altın alsaydım',
        startDate: '2015-01-01',
        amount: 20000,
        asset: 'GOLD',
        description: 'Klasik güvenli liman'
      },
      {
        id: 4,
        title: '2010\'da konut alsaydım',
        startDate: '2010-01-01',
        amount: 50000,
        asset: 'HOUSING',
        description: 'Gayrimenkul patlaması'
      }
    ];
    
    res.json({ success: true, examples });
    
  } catch (error) {
    res.status(500).json({ error: 'Örnekler yüklenemedi' });
  }
});

module.exports = router;
