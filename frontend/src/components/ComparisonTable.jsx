export default function ComparisonTable({ alternatives, selected }) {
  const formatCurrency = (value) => {
    return new Intl.NumberFormat('tr-TR', { 
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value) + ' TL';
  };

  const formatPercent = (value) => {
    return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getAssetName = (code) => {
    const names = {
      USD: '💵 Dolar', EUR: '💶 Euro', GOLD: '🪙 Altın', 
      SILVER: '⚪ Gümüş', BTC: '₿ Bitcoin', INTEREST: '🏦 Faiz',
      HOUSING: '🏠 Konut', CAR_NEW: '🚗 Sıfır Araç', CAR_USED: '🚙 İkinci El'
    };
    return names[code] || code;
  };

  return (
    <div className="card">
      <h3 className="text-xl font-bold text-slate-800 mb-4">
        📊 Tüm Alternatifler
      </h3>
      <p className="text-slate-600 mb-6">
        Aynı tutarı farklı varlıklara yatırsaydınız ne olurdu?
      </p>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b-2 border-slate-200">
              <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700">
                Varlık
              </th>
              <th className="text-right py-3 px-4 text-sm font-semibold text-slate-700">
                Bugünkü Değer
              </th>
              <th className="text-right py-3 px-4 text-sm font-semibold text-slate-700">
                Getiri
              </th>
              <th className="text-center py-3 px-4 text-sm font-semibold text-slate-700">
                Sıra
              </th>
            </tr>
          </thead>
          <tbody>
            {alternatives.map((alt, index) => (
              <tr 
                key={alt.asset}
                className={`border-b border-slate-100 hover:bg-slate-50 transition-colors ${
                  alt.asset === selected ? 'bg-primary-50 font-semibold' : ''
                }`}
              >
                <td className="py-4 px-4">
                  <div className="flex items-center gap-2">
                    {getAssetName(alt.asset)}
                    {alt.asset === selected && (
                      <span className="text-xs bg-primary-500 text-white px-2 py-1 rounded-full">
                        Seçiminiz
                      </span>
                    )}
                    {index === 0 && alt.asset !== selected && (
                      <span className="text-xs bg-gold-500 text-white px-2 py-1 rounded-full">
                        En İyi
                      </span>
                    )}
                  </div>
                </td>
                <td className="text-right py-4 px-4 font-mono">
                  {formatCurrency(alt.currentValue)}
                </td>
                <td className={`text-right py-4 px-4 font-semibold ${
                  alt.nominalReturnPercent > 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {formatPercent(alt.nominalReturnPercent)}
                </td>
                <td className="text-center py-4 px-4">
                  <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${
                    index === 0 ? 'bg-gold-500 text-white' :
                    index === 1 ? 'bg-slate-300 text-slate-700' :
                    index === 2 ? 'bg-orange-400 text-white' :
                    'bg-slate-200 text-slate-600'
                  }`}>
                    {index + 1}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
