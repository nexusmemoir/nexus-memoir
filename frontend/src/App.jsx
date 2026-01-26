import { useState } from 'react';
import Header from './components/Header';
import SimulationForm from './components/SimulationForm';
import ResultsDisplay from './components/ResultsDisplay';
import ExamplesGallery from './components/ExamplesGallery';
import Footer from './components/Footer';

function App() {
  const [simulationResult, setSimulationResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState('form'); // 'form' | 'results' | 'gallery'

  const handleSimulationComplete = (result) => {
    setSimulationResult(result);
    setView('results');
  };

  const handleNewSimulation = () => {
    setSimulationResult(null);
    setView('form');
  };

  const handleViewGallery = () => {
    setView('gallery');
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      
      <main className="flex-1 container mx-auto px-4 py-8 max-w-7xl">
        {view === 'form' && (
          <>
            <div className="text-center mb-12 animate-fade-in">
              <h1 className="text-5xl md:text-6xl font-bold text-slate-800 mb-4">
                Eğer O Gün Şöyle Yapsaydım...
              </h1>
              <p className="text-xl text-slate-600 mb-2">
                Bugün ne olurdu?
              </p>
              <p className="text-slate-500 max-w-2xl mx-auto">
                Geçmiş verilerle alternatif senaryolar simülasyonu. Sadece matematik, tavsiye yok.
              </p>
            </div>
            
            <SimulationForm 
              onComplete={handleSimulationComplete}
              loading={loading}
              setLoading={setLoading}
            />
            
            <div className="text-center mt-8">
              <button 
                onClick={handleViewGallery}
                className="text-primary-600 hover:text-primary-700 font-semibold"
              >
                📊 Popüler Senaryolara Göz Atın
              </button>
            </div>
          </>
        )}
        
        {view === 'results' && simulationResult && (
          <ResultsDisplay 
            result={simulationResult}
            onNewSimulation={handleNewSimulation}
            onViewGallery={handleViewGallery}
          />
        )}
        
        {view === 'gallery' && (
          <ExamplesGallery 
            onSelectExample={(example) => {
              setView('form');
              // Form'a örnek verileri aktar (form component'i bu veriyi alacak şekilde güncellenecek)
            }}
            onBackToForm={() => setView('form')}
          />
        )}
      </main>
      
      <Footer />
    </div>
  );
}

export default App;
