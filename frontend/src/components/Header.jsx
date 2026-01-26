import { TrendingUp } from 'lucide-react';

export default function Header() {
  return (
    <header className="bg-white border-b border-slate-200 shadow-sm">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-gradient-to-br from-primary-500 to-primary-700 p-2 rounded-lg">
            <TrendingUp className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">WhatIf TR</h1>
            <p className="text-xs text-slate-500">Alternatif Geçmiş Simülatörü</p>
          </div>
        </div>
        
        <nav className="hidden md:flex items-center gap-6">
          <a href="#nasil-calisir" className="text-slate-600 hover:text-slate-800 text-sm font-medium">
            Nasıl Çalışır?
          </a>
          <a href="#hakkinda" className="text-slate-600 hover:text-slate-800 text-sm font-medium">
            Hakkında
          </a>
        </nav>
      </div>
    </header>
  );
}
