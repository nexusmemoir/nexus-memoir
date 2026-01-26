import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import axios from 'axios';

export default function TimeSeriesChart({ startDate, endDate, asset, amount }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.post('/api/simulation/time-series', {
          startDate,
          endDate,
          asset,
          amount
        });
        
        if (response.data.success) {
          setData(response.data.series);
        }
      } catch (error) {
        console.error('Chart data error:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [startDate, endDate, asset, amount]);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('tr-TR', {
      style: 'currency',
      currency: 'TRY',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('tr-TR', { 
      year: 'numeric', 
      month: 'short' 
    });
  };

  if (loading) {
    return (
      <div className="card">
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return null;
  }

  return (
    <div className="card">
      <h3 className="text-xl font-bold text-slate-800 mb-4">
        📈 Değer Değişimi
      </h3>
      <p className="text-slate-600 mb-6">
        Yatırımınızın zaman içindeki değer grafiği
      </p>

      <div className="w-full h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis 
              dataKey="date" 
              tickFormatter={formatDate}
              stroke="#64748b"
              style={{ fontSize: '12px' }}
            />
            <YAxis 
              tickFormatter={formatCurrency}
              stroke="#64748b"
              style={{ fontSize: '12px' }}
            />
            <Tooltip 
              formatter={(value) => formatCurrency(value)}
              labelFormatter={formatDate}
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                padding: '8px'
              }}
            />
            <Line 
              type="monotone" 
              dataKey="value" 
              stroke="#0284c7" 
              strokeWidth={3}
              dot={{ fill: '#0284c7', r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 flex justify-between text-sm text-slate-600">
        <span>Başlangıç: {formatCurrency(data[0]?.value || 0)}</span>
        <span>Bitiş: {formatCurrency(data[data.length - 1]?.value || 0)}</span>
      </div>
    </div>
  );
}
