import React from 'react';
import PropTypes from 'prop-types';
import { useLanguage } from '../../contexts/LanguageContext';

/**
 * Component to display document context information in chat messages
 * This component handles dynamic translation of document context information
 */
const DocumentContextDisplay = ({ message }) => {
  const { t } = useLanguage();
  // If there's no document context, return null
  if (!message?.documentContext) return null;
  
  const { documentName, searchId, similarities = [] } = message.documentContext;
  
  // Guard against undefined values
  const safeDocName = documentName || 'Unknown';
  const safeSearchId = searchId || 'Unknown';
  // 检查消息文本中是否已有文档上下文信息
  const messageText = message.text || '';
  const hasContextInText = messageText.includes(`**[${t('usingDocumentContext')}]**`) || 
                          messageText.includes('**[Using Document Context]**') || 
                          messageText.includes('**[使用文档上下文]**') ||
                          messageText.includes('---');
  
  // 如果消息中已包含文档上下文部分，不再单独显示此组件
  if (hasContextInText) return null;
  
  return (
    <div className="mt-2 text-xs text-gray-500 border-t border-gray-200 pt-2">
      <div>
        <span className="font-semibold">{t('usingDocumentContext')}</span>
      </div>
      <div>
        <span className="font-semibold">{t('documentFilename')}:</span> {safeDocName}
      </div>
      <div>
        <span className="font-semibold">{t('searchIdLabel')}:</span> {safeSearchId}
      </div>
      {similarities && similarities.length > 0 && (
        <div>
          <span className="font-semibold">{t('similarity')}:</span> {similarities.join(', ')}
        </div>
      )}
    </div>  );
};

// Add prop validation
DocumentContextDisplay.propTypes = {
  message: PropTypes.shape({
    text: PropTypes.string,
    documentContext: PropTypes.shape({
      documentName: PropTypes.string,
      searchId: PropTypes.string,
      similarities: PropTypes.arrayOf(PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.number
      ]))
    })
  })
};

export default DocumentContextDisplay;
