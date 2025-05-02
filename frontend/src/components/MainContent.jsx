import React from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import LoadFileModule from './modules/LoadFileModule';
import ChunkFileModule from './modules/ChunkFileModule';
import ParseFileModule from './modules/ParseFileModule';
import EmbeddingFileModule from './modules/EmbeddingFileModule';
import IndexingModule from './modules/IndexingModule';
import SearchModule from './modules/SearchModule';
import GenerationModule from './modules/GenerationModule';
import ChatInterface from './modules/ChatInterface';

function MainContent({
  activeModule,
  documents,
  embeddings,
  chunks, 
  indices,
  searchResults,
  generatedText,
  loading,
  error,
  onDocumentUpload,
  onChunkDocument,
  onParseDocument,
  onCreateEmbeddings,
  onCreateIndex,
  onSearch,
  onGenerateText,
  onRefreshDocuments,
  onRefreshIndices,
  onDocumentDelete, // Add document delete handler
  onChunkDelete,    // Add chunk delete handler
  onEmbeddingDelete,// Add embedding delete handler
  onIndexDelete,    // Add index delete handler
  chatHistory, 
  config, 
  configLoading 
}) {
  const { t } = useLanguage();
  
  // 渲染活动模块
  const renderActiveModule = () => {
    switch (activeModule) {
      case 'load':
        return (
          <LoadFileModule 
            documents={documents} 
            loading={loading} 
            error={error} 
            onDocumentUpload={onDocumentUpload}
            onRefresh={onRefreshDocuments}
            onDocumentDelete={onDocumentDelete} // Pass delete handler
          />
        );
      case 'chunk':
        return (
          <ChunkFileModule 
            documents={documents} 
            chunks={chunks} 
            loading={loading} 
            error={error} 
            onChunkDocument={onChunkDocument}
            onChunkDelete={onChunkDelete} // Pass delete handler
          />
        );
      case 'parse':
        return (
          <ParseFileModule 
            documents={documents} 
            loading={loading} 
            error={error} 
            onParseDocument={onParseDocument}
          />
        );
      case 'embedding':
        return (
          <EmbeddingFileModule 
            documents={documents} 
            embeddings={embeddings} // Pass embeddings
            loading={loading} 
            error={error} 
            onCreateEmbeddings={onCreateEmbeddings}
            onEmbeddingDelete={onEmbeddingDelete} // Pass delete handler
          />
        );
      case 'indexing':
        return (
          <IndexingModule 
            embeddings={embeddings} 
            indices={indices} // Pass indices
            documents={documents} 
            loading={loading} 
            error={error} 
            onCreateIndex={onCreateIndex}
            onRefresh={onRefreshIndices}
            onIndexDelete={onIndexDelete} // Pass delete handler
          />
        );
      case 'search':
        return (
          <SearchModule 
            indices={indices} 
            documents={documents} // Pass documents for display name
            searchResults={searchResults}
            loading={loading} 
            error={error} 
            onSearch={onSearch}
          />
        );
      case 'generate':
        return (
          <GenerationModule 
            indices={indices} // Pass indices
            documents={documents} // Pass documents
            searchResults={searchResults}
            generatedText={generatedText}
            loading={loading} 
            error={error} 
            onGenerateText={onGenerateText}
            onSearch={onSearch} // Pass onSearch
          />
        );
      case 'chat':
        return (
          <ChatInterface 
            indices={indices}
            documents={documents} // Pass documents for display name
            searchResults={searchResults}
            generatedText={generatedText}
            loading={loading}
            error={error}
            onSendMessage={(message, indexId, provider, model) => {
              // First search for relevant context
              onSearch(indexId, message, 3, 0.7).then(searchResult => {
                // Then generate response based on search results
                onGenerateText(searchResult.search_id, message, provider, model, 0.7, 1024);
              });
            }}
            chatHistory={chatHistory}
          />
        );
      default:
        return <div>{t('selectModule')}</div>;
    }
  };

  return (
    <main className="flex-1 overflow-y-auto p-6 bg-white">
      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
          {t('error')}: {error}
        </div>
      )}
      {renderActiveModule()}
    </main>
  );
}

export default MainContent;

