import { useState, useEffect } from 'react';
import { Calendar, DollarSign, TrendingUp, AlertCircle } from 'lucide-react';
import axios from 'axios';

const ASSET_OPTIONS = [
  { code: 'USD', name: 'Dolar 💵', icon: '💵', category: 'Döviz' },
  { code: 'EUR', name: 'Euro 💶', icon: '💶', category: 'Döviz' },
  { code: 'GOLD', name: 'Altın 🪙', icon: '🪙', category: 'Değerli Metal' },
  { code: 'SILVER', name: 'Gümüş ⚪', icon: '⚪', category: 'Değerli Metal' },
  { code: 'BTC', name: 'Bitcoin ₿', icon: '₿', category: 'Kripto' },
  { code: 'INTEREST', name: 'Faiz 🏦', icon: '🏦', category: 'Birikim' },
  { code: 'HOUSING', name: 'Konut (m²) 🏠', icon: '🏠', category: 'Gayrimenkul' },
  { code: 'CAR_NEW', name: 'Sıfır Araç 🚗', icon: '🚗', category: 'Otomotiv' },
];

export default function SimulationForm({ onComplete, loading, setLoading }) {
  const [formData, setFormData] = useState({
    startDate: '2020-01-01',
    amount: 10000,
    asset: 'USD',
    endDate: new Date().toISOString().split('T')[0]
  });
  
  const [errors, setErrors] = useState({});
  const [showAdvanced, setShowAdvanced] = useState(false);

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.startDate) {
      newErrors.startDate = 'Tarih seçiniz';
    } else {
      const startDate = new Date(formData.startDate);
      const today = new Date();
      
      if (startDate > today) {
        newErrors.startDate = 'Gelecek tarih seçilemez';
      }
      
      if (startDate < new Date('2010-01-01')) {
        newErrors.startDate = '2010 öncesi veri mevcut değil';
      }
    }
    
    if (!formData.amount || formData.amount < 100) {
      newErrors.amount = 'Minimum 100 TL giriniz';
    }
    
    if (formData.amount > 1000000000) {
      newErrors.amount = 'Maksimum 1 milyar TL';
    }
    
    if (!formData.asset) {
      newErrors.asset = 'Varlık seçiniz';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    setLoading(true);
    
    try {
      const response = await axios.post('/api/simulation/run', {
        ...formData,
        includeLLM: true
      });
      
      if (response.data.success) {
        onComplete(response.data);
      }
    } catch (error) {
      console.error('Simulation error:', error);
      alert('Bir hata oluştu. Lütfen tekrar deneyin.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card max-w-2xl mx-auto animate-fade-in">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Tarih Seçimi */}
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-2">
            <Calendar className="inline w-4 h-4 mr-2" />
            Hangi Tarihte?
          </label>
          <input
            type="date"
            value={formData.startDate}
            onChange={(e) => setFormData({ ...formData, startDate: e.target.value })}
            max={new Date().toISOString().split('T')[0]}
            min="2010-01-01"
            className="input-field"
          />
          {errors.startDate && (
            <p className="text-red-500 text-sm mt-1 flex items-center gap-1">
              <AlertCircle className="w-4 h-4" />
              {errors.startDate}
            </p>
          )}
        </div>

        {/* Tutar Girişi */}
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-2">
            <DollarSign className="inline w-4 h-4 mr-2" />
            Ne Kadar Paranız Vardı?
          </label>
          <div className="relative">
            <input
              type="number"
              value={formData.amount}
              onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
              placeholder="10000"
              min="100"
              step="100"
              className="input-field pr-12"
            />
            <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 font-semibold">
              TL
            </span>
          </div>
          {errors.amount && (
            <p className="text-red-500 text-sm mt-1 flex items-center gap-1">
              <AlertCircle className="w-4 h-4" />
              {errors.amount}
            </p>
          )}
          <div className="flex gap-2 mt-2">
            {[1000, 5000, 10000, 50000].map(amount => (
              <button
                key={amount}
                type="button"
                onClick={() => setFormData({ ...formData, amount })}
                className="text-xs px-3 py-1 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700"
              >
                {amount.toLocaleString('tr-TR')} TL
              </button>
            ))}
          </div>
        </div>

        {/* Varlık Seçimi */}
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-2">
            <TrendingUp className="inline w-4 h-4 mr-2" />
            Neye Yatırım Yapsaydınız?
          </label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {ASSET_OPTIONS.map(option => (
              <button
                key={option.code}
                type="button"
                onClick={() => setFormData({ ...formData, asset: option.code })}
                className={`p-4 rounded-lg border-2 transition-all text-left ${
                  formData.asset === option.code
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="text-2xl mb-1">{option.icon}</div>
                <div className="font-semibold text-sm text-slate-800">{option.name}</div>
                <div className="text-xs text-slate-500">{option.category}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Gelişmiş Ayarlar */}
        <div>
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-sm text-primary-600 hover:text-primary-700 font-semibold"
          >
            {showAdvanced ? '▼' : '▶'} Gelişmiş Ayarlar
          </button>
          
          {showAdvanced && (
            <div className="mt-4 p-4 bg-slate-50 rounded-lg">
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Bitiş Tarihi (varsayılan: bugün)
              </label>
              <input
                type="date"
                value={formData.endDate}
                onChange={(e) => setFormData({ ...formData, endDate: e.target.value })}
                max={new Date().toISOString().split('T')[0]}
                min={formData.startDate}
                className="input-field"
              />
            </div>
          )}
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full text-lg"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Hesaplanıyor...
            </span>
          ) : (
            '🔮 Alternatif Geçmişi Göster'
          )}
        </button>
      </form>

      {/* Uyarı */}
      <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
        <strong>⚠️ Uyarı:</strong> Bu bir yatırım tavsiyesi değildir. Sadece geçmiş verilere dayalı matematiksel hesaplamalar gösterilmektedir.
      </div>
    </div>
  );
}
