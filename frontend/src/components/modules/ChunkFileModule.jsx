import React, { useState } from 'react';
import { useLanguage } from '../../contexts/LanguageContext'; // Import useLanguage

function ChunkFileModule({ documents, chunks = [], loading, error, onChunkDocument, onChunkDelete }) { // Add onChunkDelete prop
  const { t } = useLanguage(); // Use translation hook
  const [selectedDocument, setSelectedDocument] = useState('');
  const [strategy, setStrategy] = useState('character');
  const [chunkSize, setChunkSize] = useState(1000);
  const [overlap, setOverlap] = useState(200);
  
  // 处理表单提交
  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (!selectedDocument) {
      return;
    }
    
    onChunkDocument(selectedDocument, strategy, chunkSize, overlap)
      .then((result) => {
        // 分块成功后的处理
        console.log('分块成功:', result);
      })
      .catch((error) => {
        console.error('分块失败:', error);
      });
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-xl font-semibold mb-4">{t('documentChunking')}</h2>
        <p className="text-gray-600 mb-4">
          {t('chunkingDesc')}
        </p>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('selectDocument')}
            </label>
            <select
              value={selectedDocument}
              onChange={(e) => setSelectedDocument(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
              required
            >
              <option value="">{t('selectDocument')}</option>
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename}
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('chunkingStrategy')}
            </label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
            >
              <option value="character">{t('byCharacter')}</option>
              <option value="paragraph">{t('byParagraph')}</option>
              <option value="heading">{t('byHeading')}</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('chunkSize')}
            </label>
            <input
              type="number"
              value={chunkSize}
              onChange={(e) => setChunkSize(e.target.value)}
              min="100"
              max="10000"
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
            />
            <p className="mt-1 text-sm text-gray-500">
              {t('chunkSizeRecommended')}
            </p>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('overlapSize')}
            </label>
            <input
              type="number"
              value={overlap}
              onChange={(e) => setOverlap(e.target.value)}
              min="0"
              max="1000"
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
            />
            <p className="mt-1 text-sm text-gray-500">
              {t('overlapRecommended')}
            </p>
          </div>
          
          <div className="pt-2">
            <button
              type="submit"
              disabled={loading || !selectedDocument}
              className={`w-full px-4 py-2 text-white rounded-md ${
                loading || !selectedDocument
                  ? 'bg-purple-400 cursor-not-allowed'
                  : 'bg-purple-600 hover:bg-purple-700'
              }`}
            >
              {loading ? t('processing') : t('startChunking')}
            </button>
          </div>
        </form>
      </div>
      
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-xl font-semibold mb-4">{t('chunkingResults')}</h2>
        
        {loading ? (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-purple-600"></div>
            <p className="mt-2 text-gray-600">{t('processing')}</p>
          </div>
        ) : (
          <div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('fileName')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('strategy')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('chunkSize')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('overlapSize')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('chunks')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th> {/* Add Actions column */} 
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {Array.isArray(chunks) && chunks.map((chunk) => {
                    const doc = Array.isArray(documents) ? documents.find(d => d.id === chunk.document_id) : null;
                    return (
                      <tr key={chunk.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="font-medium text-gray-900">{doc ? doc.filename : chunk.document_id}</span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                          {chunk.strategy === 'character' ? t('byCharacter') : 
                           chunk.strategy === 'paragraph' ? t('byParagraph') : t('byHeading')}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                          {chunk.chunk_size}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                          {chunk.overlap}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                          {chunk.total_chunks}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium"> {/* Add Delete button cell */} 
                          <button 
                            onClick={() => onChunkDelete(chunk.id)} 
                            className="text-red-600 hover:text-red-900"
                          >
                            {t('delete')}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            
            {Array.isArray(chunks) && chunks.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <p>{t('noChunks')}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default ChunkFileModule;

