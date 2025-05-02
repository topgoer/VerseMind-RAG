import React from 'react';
import { useLanguage } from '../contexts/LanguageContext';

function Header() {
  const { language, toggleLanguage, t } = useLanguage();

  return (
    <header className="bg-gradient-to-r from-purple-800 to-indigo-700 text-white p-6 shadow-md">
      <div className="container mx-auto">
        <div className="flex flex-col items-center justify-center text-center">
          <h1 className="text-2xl font-bold">{t('appTitle')}</h1>
          <div className="text-2xl font-bold mt-2">{t('appSlogan')}</div>
          <span className="mt-2 text-sm bg-purple-600 px-2 py-1 rounded-full">{t('demoVersion')}</span>
        </div>
        <div className="absolute top-6 right-6">
          <button 
            onClick={toggleLanguage}
            className="px-3 py-1 bg-purple-600 hover:bg-purple-700 rounded text-sm transition-colors"
          >
            {language === 'en' ? t('switchToChinese') : t('switchToEnglish')}
          </button>
        </div>
      </div>
    </header>
  );
}

export default Header;
