export default function PurchasingPowerCard({ purchasingPower }) {
  if (!purchasingPower || purchasingPower.length === 0) {
    return null;
  }

  return (
    <div className="card">
      <h3 className="text-xl font-bold text-slate-800 mb-4">
        🛒 Satın Alma Gücü
      </h3>
      <p className="text-slate-600 mb-6">
        Aynı miktar parayla o gün ve bugün ne alabilirdiniz?
      </p>

      <div className="grid md:grid-cols-3 gap-4">
        {purchasingPower.map((item, index) => (
          <div key={index} className="stat-card">
            <div className="text-center mb-3">
              <p className="text-sm font-semibold text-slate-700">{item.item}</p>
            </div>
            
            <div className="space-y-3">
              <div className="bg-blue-50 p-3 rounded-lg">
                <p className="text-xs text-slate-600 mb-1">O Gün</p>
                <p className="text-2xl font-bold text-blue-700">
                  {item.then.toFixed(1)} <span className="text-sm">{item.unit}</span>
                </p>
              </div>
              
              <div className="bg-slate-50 p-3 rounded-lg">
                <p className="text-xs text-slate-600 mb-1">Bugün</p>
                <p className="text-2xl font-bold text-slate-700">
                  {item.now.toFixed(1)} <span className="text-sm">{item.unit}</span>
                </p>
              </div>
              
              <div className={`text-center p-2 rounded-lg ${
                item.change > 0 ? 'bg-red-50' : 'bg-green-50'
              }`}>
                <p className={`text-sm font-semibold ${
                  item.change > 0 ? 'text-red-600' : 'text-green-600'
                }`}>
                  {item.change > 0 ? '📉' : '📈'} {Math.abs(item.change)}% 
                  {item.change > 0 ? ' daha az' : ' daha fazla'}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
        <p className="text-sm text-yellow-800">
          <strong>💡 Not:</strong> Negatif değer satın alma gücünüzün azaldığını, 
          pozitif değer arttığını gösterir. Bu enflasyonun etkisini somutlaştırır.
        </p>
      </div>
    </div>
  );
}
