export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-white border-t border-slate-200 mt-12">
      <div className="container mx-auto px-4 py-8">
        <div className="grid md:grid-cols-3 gap-8 mb-8">
          {/* Hakkında */}
          <div>
            <h3 className="font-bold text-slate-800 mb-3">WhatIf TR</h3>
            <p className="text-sm text-slate-600">
              Geçmiş verilerle alternatif senaryolar simülasyonu. 
              Sadece matematik, tavsiye yok.
            </p>
          </div>

          {/* Nasıl Çalışır */}
          <div id="nasil-calisir">
            <h3 className="font-bold text-slate-800 mb-3">Nasıl Çalışır?</h3>
            <ul className="text-sm text-slate-600 space-y-2">
              <li>✅ Geçmiş bir tarih seçin</li>
              <li>✅ O güne göre bir tutar girin</li>
              <li>✅ Bir varlık seçin</li>
              <li>✅ Bugünkü değeri ve alternatifleri görün</li>
            </ul>
          </div>

          {/* Uyarılar */}
          <div id="hakkinda">
            <h3 className="font-bold text-slate-800 mb-3">Önemli Uyarılar</h3>
            <ul className="text-sm text-slate-600 space-y-2">
              <li>⚠️ Yatırım tavsiyesi değildir</li>
              <li>⚠️ Gelecek tahmini yoktur</li>
              <li>⚠️ Sadece geçmiş veriler</li>
              <li>⚠️ Eğitim amaçlıdır</li>
            </ul>
          </div>
        </div>

        <div className="border-t border-slate-200 pt-6 flex flex-col md:flex-row justify-between items-center text-sm text-slate-500">
          <p>© {currentYear} WhatIf TR. Tüm hakları saklıdır.</p>
          <div className="flex gap-4 mt-4 md:mt-0">
            <a href="#" className="hover:text-slate-700">Gizlilik</a>
            <a href="#" className="hover:text-slate-700">Kullanım Koşulları</a>
            <a href="#" className="hover:text-slate-700">İletişim</a>
          </div>
        </div>

        <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-xs text-yellow-800">
          <strong>Yasal Uyarı:</strong> Bu platform sadece geçmiş verilere dayalı matematiksel hesaplamalar yapar. 
          Gelecek tahmini içermez. Yatırım kararlarınızı profesyonel danışmanlık alarak vermeniz önerilir. 
          Bu sitede yer alan bilgiler yatırım, vergi veya hukuki tavsiye niteliği taşımaz.
        </div>
      </div>
    </footer>
  );
}
