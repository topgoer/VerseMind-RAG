import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { useLanguage } from '../../contexts/LanguageContext';

function ParseFileModule({
  documents,
  onParseDocument,
  loading,
  error,
  availableParsers
}) {
  const { t } = useLanguage();
  const [selectedDocument, setSelectedDocument] = useState('');
  const [strategy, setStrategy] = useState('full_text');
  const [extractTables, setExtractTables] = useState(true);
  const [extractImages, setExtractImages] = useState(true);
  const [parseResult, setParseResult] = useState(null);
  
  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (!selectedDocument) {
      return;
    }
    
    onParseDocument(selectedDocument, strategy, extractTables, extractImages)
      .then((result) => {
        // Handle successful parsing
        setParseResult(result);
      })
      .catch((error) => {
        console.error(t('parsingFailed') + ':', error);
      });
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-xl font-semibold mb-4">{t('documentParsing')}</h2>
        <p className="text-gray-600 mb-4">
          {t('parsingDesc')}
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
              {t('parsingStrategy')}
            </label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
            >
              <option value="full_text">{t('fullParsing')}</option>
              <option value="by_page">{t('pageParsing')}</option>
              <option value="by_heading">{t('headingParsing')}</option>
            </select>
          </div>
          
          <div className="flex items-center">
            <input
              id="extractTables"
              type="checkbox"
              checked={extractTables}
              onChange={(e) => setExtractTables(e.target.checked)}
              className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300 rounded"
            />
            <label htmlFor="extractTables" className="ml-2 block text-sm text-gray-700">
              {t('extractTables')}
            </label>
          </div>
          
          <div className="flex items-center">
            <input
              id="extractImages"
              type="checkbox"
              checked={extractImages}
              onChange={(e) => setExtractImages(e.target.checked)}
              className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300 rounded"
            />
            <label htmlFor="extractImages" className="ml-2 block text-sm text-gray-700">
              {t('extractImages')}
            </label>
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
              {loading ? t('processing') : t('startParsing')}
            </button>
          </div>
        </form>
      </div>
      
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-xl font-semibold mb-4">{t('parsingResults')}</h2>
        
        {loading ? (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-purple-600"></div>
            <p className="mt-2 text-gray-600">{t('loading')}</p>
          </div>
        ) : parseResult ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 p-4 rounded">
                <h3 className="font-medium text-gray-700 mb-2">{t('documentInfo')}</h3>
                <p><span className="text-gray-500">{t('documentId')}</span> {parseResult.document_id}</p>
                <p><span className="text-gray-500">{t('parseId')}</span> {parseResult.parse_id}</p>
                <p><span className="text-gray-500">{t('strategy')}:</span> {
                  parseResult.strategy === 'full_text' ? t('fullParsing') : 
                  parseResult.strategy === 'by_page' ? t('pageParsing') : 
                  parseResult.strategy === 'by_heading' ? t('headingParsing') : t('textAndTables')
                }</p>
              </div>
              
              <div className="bg-gray-50 p-4 rounded">
                <h3 className="font-medium text-gray-700 mb-2">{t('contentStats')}</h3>
                <p><span className="text-gray-500">{t('sectionCount')}</span> {parseResult.total_sections}</p>
                <p><span className="text-gray-500">{t('paragraphCount')}</span> {parseResult.total_paragraphs}</p>
                <p><span className="text-gray-500">{t('tableCount')}</span> {parseResult.total_tables}</p>
                <p><span className="text-gray-500">{t('imageCount')}</span> {parseResult.total_images}</p>
              </div>
            </div>
            
            <div className="bg-gray-50 p-4 rounded">
              <h3 className="font-medium text-gray-700 mb-2">{t('parsingExample')}</h3>
              <div className="bg-white p-3 border border-gray-200 rounded text-sm">
                <p className="text-gray-700">
                  {t('documentParsed1', { 
                    paragraphs: parseResult.total_paragraphs, 
                    sections: parseResult.total_sections,
                    tables: parseResult.total_tables || 0,
                    images: parseResult.total_images || 0
                  })}
                </p>
                {parseResult.parsed_content && parseResult.parsed_content.length > 0 && (
                  <div className="mt-2">
                    <h4 className="font-medium text-gray-700 mb-1">{t('contentSample')}</h4>
                    <div className="bg-gray-50 p-2 border border-gray-200 rounded max-h-60 overflow-auto">
                      {parseResult.parsed_content.map((item, idx) => (
                        <div key={`content-preview-${idx}`} className="mb-2">
                          {item.type === 'heading' && (
                            <p className={`font-medium ${item.level > 1 ? 'ml-' + (item.level * 2) : ''}`}>
                              {item.text}
                            </p>
                          )}
                          {item.type === 'paragraph' && (
                            <p className="text-sm text-gray-600">
                              {item.text.substring(0, 200)}{item.text.length > 200 ? '...' : ''}
                            </p>
                          )}
                          {item.type === 'table' && (
                            <p className="text-sm text-gray-600 italic">
                              {t('tableData')}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <p>{t('noParsing')}</p>
          </div>
        )}
        
        {error && (
          <div className="p-4 mt-4 text-sm text-red-700 bg-red-100 rounded-lg" role="alert">
            <span className="font-medium">{t('error')}!</span> {error}
          </div>
        )}
      </div>
    </div>
  );
}

ParseFileModule.propTypes = {
  documents: PropTypes.array.isRequired,
  onParseDocument: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  error: PropTypes.string,
  availableParsers: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      description: PropTypes.string.isRequired,
    })
  )
};

ParseFileModule.defaultProps = {
  loading: false,
  error: null,
  availableParsers: []
};

export default ParseFileModule;
