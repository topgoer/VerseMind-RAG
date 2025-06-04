import React from 'react';
import PropTypes from 'prop-types';
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
  chunksLoading,
  chunksError,
  indices,
  searchResults,
  generatedText,
  loading,
  error,
  onDocumentUpload,
  onDocumentDelete, // Add this prop
  onChunkDocument,
  onParseDocument,
  onCreateEmbeddings,
  onLoadEmbeddings,    // Add this to receive the prop from App.jsx
  onCreateIndex,
  onSearch,
  onGenerateText,
  onSendMessage, // Added from App.jsx
  onRefreshDocuments,
  onRefreshIndices,
  onChunkDelete,
  onEmbeddingDelete,
  onIndexDelete,
  chatHistory, 
  currentTask, // Added from App.jsx
  taskProgress, // Added from App.jsx
  config, 
  configLoading,
  selectedDocumentObject,
  onDocumentSelect
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
            onDocumentDelete={onDocumentDelete} // Pass it down
            onRefresh={onRefreshDocuments}
          />
        );
      case 'parse':
        return (
          <ParseFileModule 
            documents={documents}
            chunks={chunks}
            loading={loading || chunksLoading} 
            error={error || chunksError} 
            onParseDocument={onParseDocument}
          />
        );
      case 'chunk':
        return (
          <ChunkFileModule 
            documents={documents}
            chunks={chunks}
            loading={loading || chunksLoading}
            error={error || chunksError}
            onChunkDocument={onChunkDocument}
            onChunkDelete={onChunkDelete}
            selectedDocumentObject={selectedDocumentObject}
            onDocumentSelect={onDocumentSelect}
          />
        );
      case 'embedding':
        return (
          <EmbeddingFileModule 
            documents={documents}
            chunks={chunks}
            embeddings={embeddings} // Pass embeddings
            loading={loading || chunksLoading} 
            error={error || chunksError}  
            onCreateEmbeddings={onCreateEmbeddings}
            onLoadEmbeddings={onLoadEmbeddings} // Pass onLoadEmbeddings
            onEmbeddingDelete={onEmbeddingDelete} // Pass delete handler
            globalSelectedDocument={selectedDocumentObject}
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
            onLoadEmbeddings={onLoadEmbeddings} // Add missing property to load embeddings
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
            documents={documents} // Add documents prop to match GenerationModule
            loading={loading}
            error={error}
            onSendMessage={onSendMessage}
            chatHistory={chatHistory}
            currentTask={currentTask}
            taskProgress={taskProgress}
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

MainContent.propTypes = {
  activeModule: PropTypes.string.isRequired,
  documents: PropTypes.array.isRequired,
  embeddings: PropTypes.array.isRequired,
  chunks: PropTypes.array.isRequired,
  indices: PropTypes.array.isRequired,
  searchResults: PropTypes.object,
  generatedText: PropTypes.string,
  loading: PropTypes.bool.isRequired,
  error: PropTypes.string,
  onDocumentUpload: PropTypes.func.isRequired,
  onDocumentDelete: PropTypes.func.isRequired,
  onChunkDocument: PropTypes.func.isRequired,
  onParseDocument: PropTypes.func.isRequired,
  onCreateEmbeddings: PropTypes.func.isRequired,
  onLoadEmbeddings: PropTypes.func.isRequired,
  onCreateIndex: PropTypes.func.isRequired,
  onSearch: PropTypes.func.isRequired,
  onGenerateText: PropTypes.func.isRequired,
  onSendMessage: PropTypes.func.isRequired,
  onRefreshDocuments: PropTypes.func.isRequired,
  onRefreshIndices: PropTypes.func.isRequired,
  onChunkDelete: PropTypes.func.isRequired,
  onEmbeddingDelete: PropTypes.func.isRequired,
  onIndexDelete: PropTypes.func.isRequired,
  chatHistory: PropTypes.array.isRequired,
  currentTask: PropTypes.string,
  taskProgress: PropTypes.number,
  config: PropTypes.object,
  configLoading: PropTypes.bool,
  selectedDocumentObject: PropTypes.object,
  onDocumentSelect: PropTypes.func
};

export default MainContent;

