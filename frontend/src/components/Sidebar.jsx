import React from 'react';
import PropTypes from 'prop-types';
import { useLanguage } from '../contexts/LanguageContext';

function Sidebar({ activeModule, onModuleChange }) {
  const { t } = useLanguage();
  
  // 定义模块列表
  const modules = [
    { id: 'chat', name: t('moduleChat'), icon: '💬' },
    { id: 'load', name: t('moduleLoad'), icon: '📄' },
    { id: 'chunk', name: t('moduleChunk'), icon: '✂️' },      // chunk 提前
    { id: 'parse', name: t('moduleParse'), icon: '🔍' },      // parse 后移
    { id: 'embedding', name: t('moduleEmbedding'), icon: '🧠' },
    { id: 'indexing', name: t('moduleIndexing'), icon: '📊' },
    { id: 'search', name: t('moduleSearch'), icon: '🔎' },
    { id: 'generate', name: t('moduleGenerate'), icon: '✨' },
    { id: 'wechat-downloader', name: t('moduleWechatDownloader'), icon: '📱' },
  ];

  return (
    <aside className="w-64 bg-gray-800 text-white p-4 overflow-y-auto">
      <div className="mb-6">
        <h2 className="text-xl font-semibold mb-2">{t('modules')}</h2>
        <p className="text-gray-400 text-sm">{t('selectModule')}</p>
      </div>
      
      <nav>
        <ul>
          {modules.map((module) => (
            <li key={module.id} className="mb-2">
              <button
                onClick={() => onModuleChange(module.id)}
                className={`w-full text-left px-4 py-2 rounded transition-colors flex items-center ${
                  activeModule === module.id
                    ? 'bg-purple-700 text-white'
                    : 'text-gray-300 hover:bg-gray-700'
                }`}
              >
                <span className="mr-3">{module.icon}</span>
                {module.name}
              </button>
            </li>
          ))}
        </ul>
      </nav>
      
      <div className="mt-auto pt-6 border-t border-gray-700 text-xs text-gray-500">
        <p className="mb-1">{t('appTitle')}</p>
        <p>{t('copyright')}</p>
      </div>
    </aside>
  );
}

Sidebar.propTypes = {
  activeModule: PropTypes.string.isRequired,
  onModuleChange: PropTypes.func.isRequired,
};

export default Sidebar;
