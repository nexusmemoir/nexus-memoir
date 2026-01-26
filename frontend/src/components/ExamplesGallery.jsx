import { useState, useEffect } from 'react';
import { ArrowLeft, TrendingUp } from 'lucide-react';
import axios from 'axios';

export default function ExamplesGallery({ onSelectExample, onBackToForm }) {
  const [examples, setExamples] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchExamples = async () => {
      try {
        const response = await axios.get('/api/simulation/examples');
        if (response.data.success) {
          setExamples(response.data.examples);
        }
      } catch (error) {
        console.error('Examples error:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchExamples();
  }, []);

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto" />
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <button 
          onClick={onBackToForm}
          className="flex items-center gap-2 text-primary-600 hover:text-primary-700 font-semibold mb-4"
        >
          <ArrowLeft className="w-5 h-5" />
          Geri Dön
        </button>
        
        <h2 className="text-4xl font-bold text-slate-800 mb-2">
          Popüler Senaryolar
        </h2>
        <p className="text-slate-600">
          Diğer kullanıcıların ilginç bulduğu "keşke" senaryoları
        </p>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {examples.map((example) => (
          <div 
            key={example.id}
            className="card hover:shadow-xl transition-all cursor-pointer group"
            onClick={() => onSelectExample(example)}
          >
            <div className="flex items-start justify-between mb-4">
              <h3 className="text-lg font-bold text-slate-800 group-hover:text-primary-600 transition-colors">
                {example.title}
              </h3>
              <TrendingUp className="w-5 h-5 text-primary-500" />
            </div>
            
            <p className="text-slate-600 text-sm mb-4">
              {example.description}
            </p>
            
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">Tarih:</span>
                <span className="font-semibold">{example.startDate}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Tutar:</span>
                <span className="font-semibold">
                  {example.amount.toLocaleString('tr-TR')} TL
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Varlık:</span>
                <span className="font-semibold">{example.asset}</span>
              </div>
            </div>
            
            <button className="w-full mt-4 py-2 bg-primary-50 hover:bg-primary-100 text-primary-700 font-semibold rounded-lg transition-colors">
              Bu Senaryoyu Dene
            </button>
          </div>
        ))}
      </div>

      {examples.length === 0 && (
        <div className="text-center py-12">
          <p className="text-slate-500">Henüz popüler senaryo yok.</p>
        </div>
      )}
    </div>
  );
}
