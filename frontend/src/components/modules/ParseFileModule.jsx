import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { useLanguage } from '../../contexts/LanguageContext';

// This hook encapsulates the chunked document filtering logic
function useChunkedDocuments(chunks, documents, selectedDocument, setSelectedDocument) {
  const [chunkedDocuments, setChunkedDocuments] = useState([]);
  
  useEffect(() => {
    if (!Array.isArray(chunks) || !Array.isArray(documents)) {
      setChunkedDocuments([]);
      return;
    }

    // Extract unique document IDs from chunks
    const chunkedDocumentIds = [...new Set(chunks.map(chunk => chunk.document_id))];
    
    // Filter the documents array to only include documents that have chunks
    const filteredDocuments = documents.filter(doc => chunkedDocumentIds.includes(doc.id));
    
    setChunkedDocuments(filteredDocuments);
    
    // If the currently selected document is not in the filtered list, reset selection
    if (selectedDocument && !chunkedDocumentIds.includes(selectedDocument)) {
      setSelectedDocument('');
    }
  }, [chunks, documents, selectedDocument, setSelectedDocument]);
  
  return chunkedDocuments;
}

function ParseFileModule({
  documents,
  chunks = [],
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
  
  const chunkedDocuments = useChunkedDocuments(
    chunks, 
    documents, 
    selectedDocument, 
    setSelectedDocument
  );
  
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
      <ParsingForm 
        chunkedDocuments={chunkedDocuments}
        selectedDocument={selectedDocument}
        setSelectedDocument={setSelectedDocument}
        strategy={strategy}
        setStrategy={setStrategy}
        extractTables={extractTables}
        setExtractTables={setExtractTables}
        extractImages={extractImages}
        setExtractImages={setExtractImages}
        loading={loading}
        handleSubmit={handleSubmit}
        t={t}
      />
      
      <ParsingResults
        parseResult={parseResult}
        loading={loading}
        error={error}
        t={t}
      />
    </div>
  );
}

// Component for the parsing form
function ParsingForm({
  chunkedDocuments,
  selectedDocument,
  setSelectedDocument,
  strategy,
  setStrategy,
  extractTables,
  setExtractTables,
  extractImages,
  setExtractImages,
  loading,
  handleSubmit,
  t
}) {
  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h2 className="text-xl font-semibold mb-4">{t('documentParsing')}</h2>
      <p className="text-gray-600 mb-4">
        {t('parsingDesc')}
      </p>
      {chunkedDocuments.length === 0 && (
        <div className="p-4 mb-4 text-sm text-amber-700 bg-amber-100 rounded-lg" role="alert">
          <span className="font-medium">{t('info') || 'Info'}:</span> {t('noChunkedDocumentsAlert') || 'You need to chunk documents before parsing them. Please go to the chunking module first and process your documents.'}
        </div>
      )}
      
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
            {chunkedDocuments.length > 0 ? (
              chunkedDocuments.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename}
                </option>
              ))
            ) : (
              <option disabled value="">
                {t('noChunkedDocuments') || 'No chunked documents available. Please chunk documents first.'}
              </option>
            )}
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
          {/* Extract ternary into a separate variable for better readability */}
          {(() => {
            const isDisabled = loading || !selectedDocument;
            const buttonClass = isDisabled
              ? 'bg-purple-400 cursor-not-allowed'
              : 'bg-purple-600 hover:bg-purple-700';
            
            return (
              <button
                type="submit"
                disabled={isDisabled}
                className={`w-full px-4 py-2 text-white rounded-md ${buttonClass}`}
              >
                {(() => {
                  const buttonText = loading ? t('processing') : t('startParsing');
                  return buttonText;
                })()}
              </button>
            );
          })()}
        </div>
      </form>
    </div>
  );
}

// Component for displaying parsing results
function ParsingResults({ parseResult, loading, error, t }) {
  // Helper function to get strategy display text
  const getStrategyDisplayText = (strategy) => {
    if (strategy === 'full_text') return t('fullParsing');
    if (strategy === 'by_page') return t('pageParsing');
    if (strategy === 'by_heading') return t('headingParsing');
    return t('textAndTables');
  };
  
  // Helper function to render content items
  const renderContentItem = (item, idx) => {
    if (item.type === 'heading') {
      // Extract className logic to variable
      const headingIndent = item.level > 1 ? 'ml-' + (item.level * 2) : '';
      return (
        <p className={`font-medium ${headingIndent}`}>
          {item.text}
        </p>
      );
    }
    if (item.type === 'paragraph') {
      // Extract text truncation logic
      const displayText = item.text.substring(0, 200);
      const ellipsis = item.text.length > 200 ? '...' : '';
      
      return (
        <p className="text-sm text-gray-600">
          {displayText}{ellipsis}
        </p>
      );
    }
    if (item.type === 'table') {
      return (
        <p className="text-sm text-gray-600 italic">
          {t('tableData')}
        </p>
      );
    }
    return null;
  };
  
  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h2 className="text-xl font-semibold mb-4">{t('parsingResults')}</h2>
      
      {/* Extract complex nested ternary into separate render methods */}
      {(() => {
        // Loading state
        if (loading) {
          return (
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-purple-600"></div>
              <p className="mt-2 text-gray-600">{t('loading')}</p>
            </div>
          );
        }
        
        // Results state
        if (parseResult) {
          return (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 p-4 rounded">
                  <h3 className="font-medium text-gray-700 mb-2">{t('documentInfo')}</h3>
                  <p><span className="text-gray-500">{t('documentId')}</span> {parseResult.document_id}</p>
                  <p><span className="text-gray-500">{t('parseId')}</span> {parseResult.parse_id}</p>
                  <p>
                    <span className="text-gray-500">{t('strategy')}:</span> {getStrategyDisplayText(parseResult.strategy)}
                  </p>
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
                          <div key={`content-${item.type}-${item.text?.substring(0, 20)}-${idx}`} className="mb-2">
                            {renderContentItem(item, idx)}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        }
        
        // No results state
        return (
          <div className="text-center py-8 text-gray-500">
            <p>{t('noParsing')}</p>
          </div>
        );
      })()}
      
      {error && (
        <div className="p-4 mt-4 text-sm text-red-700 bg-red-100 rounded-lg" role="alert">
          <span className="font-medium">{t('error')}!</span> {error}
        </div>
      )}
    </div>
  );
}

// PropTypes for all components
ParseFileModule.propTypes = {
  documents: PropTypes.array.isRequired,
  chunks: PropTypes.array,
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

ParsingForm.propTypes = {
  chunkedDocuments: PropTypes.array.isRequired,
  selectedDocument: PropTypes.string.isRequired,
  setSelectedDocument: PropTypes.func.isRequired,
  strategy: PropTypes.string.isRequired,
  setStrategy: PropTypes.func.isRequired,
  extractTables: PropTypes.bool.isRequired,
  setExtractTables: PropTypes.func.isRequired,
  extractImages: PropTypes.bool.isRequired,
  setExtractImages: PropTypes.func.isRequired,
  loading: PropTypes.bool.isRequired,
  handleSubmit: PropTypes.func.isRequired,
  t: PropTypes.func.isRequired
};

ParsingResults.propTypes = {
  parseResult: PropTypes.object,
  loading: PropTypes.bool.isRequired,
  error: PropTypes.string,
  t: PropTypes.func.isRequired
};

ParseFileModule.defaultProps = {
  loading: false,
  error: null,
  availableParsers: []
};

export default ParseFileModule;
