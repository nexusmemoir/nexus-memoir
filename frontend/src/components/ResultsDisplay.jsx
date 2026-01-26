import { useState } from 'react';
import { TrendingUp, TrendingDown, Share2, RotateCcw, Info } from 'lucide-react';
import ComparisonTable from './ComparisonTable';
import PurchasingPowerCard from './PurchasingPowerCard';
import TimeSeriesChart from './TimeSeriesChart';

export default function ResultsDisplay({ result, onNewSimulation, onViewGallery }) {
  const { simulation, analysis } = result;
  const { selected, alternatives, inflation, purchasingPower, period } = simulation;
  
  const [showChart, setShowChart] = useState(false);
  
  const isProfit = selected.nominalReturnPercent > 0;
  const realReturn = ((1 + selected.nominalReturnPercent / 100) / (1 + inflation / 100) - 1) * 100;
  const isRealProfit = realReturn > 0;
  
  const best = alternatives[0];
  const worst = alternatives[alternatives.length - 1];
  const opportunityCost = best.currentValue - selected.currentValue;

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('tr-TR', { 
      style: 'currency', 
      currency: 'TRY',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatPercent = (value) => {
    return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getAssetName = (code) => {
    const names = {
      USD: 'Dolar', EUR: 'Euro', GOLD: 'Altın', SILVER: 'Gümüş',
      BTC: 'Bitcoin', INTEREST: 'Faiz', HOUSING: 'Konut', 
      CAR_NEW: 'Sıfır Araç', CAR_USED: 'İkinci El Araç'
    };
    return names[code] || code;
  };

  const handleShare = async () => {
    const text = `${period.start} tarihinde ${formatCurrency(selected.initialAmount)} ${getAssetName(selected.asset)} alsaydım bugün ${formatCurrency(selected.currentValue)} olurdu! #KeşkeHesap #WhatIfTR`;
    
    if (navigator.share) {
      try {
        await navigator.share({ text, url: window.location.href });
      } catch (err) {
        console.log('Share cancelled');
      }
    } else {
      navigator.clipboard.writeText(text);
      alert('Link kopyalandı!');
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Ana Başlık */}
      <div className="text-center">
        <h2 className="text-4xl font-bold text-slate-800 mb-2">
          Simülasyon Sonucu
        </h2>
        <p className="text-slate-600">
          {period.start} → {period.end} ({period.days} gün)
        </p>
      </div>

      {/* Ana Sonuç Kartı */}
      <div className="card bg-gradient-to-br from-primary-50 to-white border-2 border-primary-200">
        <div className="text-center mb-6">
          <p className="text-slate-600 mb-2">
            {period.start} tarihinde {formatCurrency(selected.initialAmount)} değerinde
          </p>
          <h3 className="text-3xl font-bold text-primary-700 mb-4">
            {getAssetName(selected.asset)} alsaydınız
          </h3>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Nominal Sonuç */}
          <div className="text-center p-6 bg-white rounded-xl shadow-sm">
            <p className="text-sm text-slate-600 mb-2">Bugünkü Değer</p>
            <p className="text-4xl font-bold text-slate-800 mb-2 animate-count-up">
              {formatCurrency(selected.currentValue)}
            </p>
            <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full ${
              isProfit ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
            }`}>
              {isProfit ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
              <span className="font-semibold">{formatPercent(selected.nominalReturnPercent)}</span>
            </div>
            <p className="text-xs text-slate-500 mt-2">Nominal Getiri</p>
          </div>

          {/* Reel Sonuç */}
          <div className="text-center p-6 bg-white rounded-xl shadow-sm border-2 border-yellow-200">
            <div className="flex items-center justify-center gap-2 mb-2">
              <p className="text-sm text-slate-600">Reel Getiri</p>
              <div className="tooltip">
                <Info className="w-4 h-4 text-slate-400" />
                <span className="tooltip-text">
                  Enflasyon ayarlı gerçek kazanç/kayıp. Bu dönemde enflasyon {formatPercent(inflation)} oldu.
                </span>
              </div>
            </div>
            <p className="text-3xl font-bold mb-2">
              {formatPercent(realReturn)}
            </p>
            <p className="text-sm text-slate-600">
              {isRealProfit ? 
                '🎉 Satın alma gücünüz arttı!' : 
                '📉 Satın alma gücünüz azaldı'
              }
            </p>
            <p className="text-xs text-slate-500 mt-2">
              Enflasyon: {formatPercent(inflation)}
            </p>
          </div>
        </div>

        {/* Özet Mesaj */}
        <div className="mt-6 p-4 bg-slate-50 rounded-lg">
          <p className="text-slate-700 text-center">
            {isProfit && isRealProfit && '✅ Hem nominal hem de reel olarak kazandınız.'}
            {isProfit && !isRealProfit && '⚠️ Nominal olarak kazandınız ama satın alma gücünüz azaldı.'}
            {!isProfit && '❌ Nominal olarak kaybettiniz.'}
          </p>
        </div>
      </div>

      {/* LLM Analizi */}
      {analysis && (
        <div className="card">
          <h3 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
            <span>🤖</span> Detaylı Analiz
          </h3>
          <div className="prose prose-slate max-w-none">
            {analysis.text.split('\n').map((paragraph, i) => (
              <p key={i} className="text-slate-700 mb-3">{paragraph}</p>
            ))}
          </div>
          {analysis.tokens > 0 && (
            <p className="text-xs text-slate-400 mt-4">
              AI tarafından oluşturuldu • {analysis.model}
            </p>
          )}
        </div>
      )}

      {/* Alternatifler */}
      {opportunityCost > 0 && (
        <div className="card bg-gradient-to-br from-red-50 to-white border-2 border-red-200">
          <h3 className="text-xl font-bold text-red-700 mb-4">
            ⚠️ Kaçırılan Fırsat
          </h3>
          <p className="text-slate-700 mb-4">
            Aynı dönemde <strong>{getAssetName(best.asset)}</strong> alsaydınız{' '}
            <strong className="text-2xl text-red-700">{formatCurrency(best.currentValue)}</strong> olurdu.
          </p>
          <div className="p-4 bg-white rounded-lg">
            <p className="text-sm text-slate-600 mb-1">Fırsat Maliyeti</p>
            <p className="text-3xl font-bold text-red-600">
              {formatCurrency(opportunityCost)}
            </p>
          </div>
        </div>
      )}

      {/* Karşılaştırma Tablosu */}
      <ComparisonTable alternatives={alternatives} selected={selected.asset} />

      {/* Satın Alma Gücü */}
      <PurchasingPowerCard purchasingPower={purchasingPower} />

      {/* Grafik (Opsiyonel) */}
      {showChart && (
        <TimeSeriesChart 
          startDate={period.start}
          endDate={period.end}
          asset={selected.asset}
          amount={selected.initialAmount}
        />
      )}

      {/* Aksiyon Butonları */}
      <div className="flex flex-col md:flex-row gap-4">
        <button onClick={onNewSimulation} className="btn-primary flex-1">
          <RotateCcw className="inline w-5 h-5 mr-2" />
          Yeni Simülasyon
        </button>
        
        <button onClick={handleShare} className="btn-secondary flex-1">
          <Share2 className="inline w-5 h-5 mr-2" />
          Paylaş
        </button>
        
        <button 
          onClick={() => setShowChart(!showChart)} 
          className="btn-secondary flex-1"
        >
          {showChart ? 'Grafiği Gizle' : '📈 Grafiği Göster'}
        </button>
      </div>
    </div>
  );
}
