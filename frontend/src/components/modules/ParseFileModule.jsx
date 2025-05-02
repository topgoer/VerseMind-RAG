import React, { useState } from 'react';

function ParseFileModule({ documents, loading, error, onParseDocument }) {
  const [selectedDocument, setSelectedDocument] = useState('');
  const [strategy, setStrategy] = useState('full');
  const [extractTables, setExtractTables] = useState(true);
  const [extractImages, setExtractImages] = useState(true);
  const [parseResult, setParseResult] = useState(null);
  
  // 处理表单提交
  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (!selectedDocument) {
      return;
    }
    
    onParseDocument(selectedDocument, strategy, extractTables, extractImages)
      .then((result) => {
        // 解析成功后的处理
        setParseResult(result);
      })
      .catch((error) => {
        console.error('解析失败:', error);
      });
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-xl font-semibold mb-4">文档解析</h2>
        <p className="text-gray-600 mb-4">
          分析文档结构，提取段落、标题、表格和图像。
        </p>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              选择文档
            </label>
            <select
              value={selectedDocument}
              onChange={(e) => setSelectedDocument(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
              required
            >
              <option value="">-- 请选择文档 --</option>
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename}
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              解析策略
            </label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
            >
              <option value="full">全文解析</option>
              <option value="page">分页解析</option>
              <option value="heading">标题结构解析</option>
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
              提取表格
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
              提取图像
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
              {loading ? '处理中...' : '开始解析'}
            </button>
          </div>
        </form>
      </div>
      
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-xl font-semibold mb-4">解析结果</h2>
        
        {loading ? (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-purple-600"></div>
            <p className="mt-2 text-gray-600">处理中...</p>
          </div>
        ) : parseResult ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 p-4 rounded">
                <h3 className="font-medium text-gray-700 mb-2">文档信息</h3>
                <p><span className="text-gray-500">文档ID:</span> {parseResult.document_id}</p>
                <p><span className="text-gray-500">解析ID:</span> {parseResult.parse_id}</p>
                <p><span className="text-gray-500">策略:</span> {
                  parseResult.strategy === 'full' ? '全文解析' : 
                  parseResult.strategy === 'page' ? '分页解析' : '标题结构解析'
                }</p>
              </div>
              
              <div className="bg-gray-50 p-4 rounded">
                <h3 className="font-medium text-gray-700 mb-2">内容统计</h3>
                <p><span className="text-gray-500">章节数:</span> {parseResult.total_sections}</p>
                <p><span className="text-gray-500">段落数:</span> {parseResult.total_paragraphs}</p>
                <p><span className="text-gray-500">表格数:</span> {parseResult.total_tables}</p>
                <p><span className="text-gray-500">图像数:</span> {parseResult.total_images}</p>
              </div>
            </div>
            
            <div className="bg-gray-50 p-4 rounded">
              <h3 className="font-medium text-gray-700 mb-2">解析示例</h3>
              <div className="bg-white p-3 border border-gray-200 rounded text-sm">
                <p className="text-gray-700">文档已成功解析，提取了 {parseResult.total_paragraphs} 个段落、{parseResult.total_sections} 个章节{parseResult.total_tables > 0 ? `、${parseResult.total_tables} 个表格` : ''}{parseResult.total_images > 0 ? `和 ${parseResult.total_images} 张图像` : ''}。</p>
                <p className="text-gray-700 mt-2">解析结果已保存，可用于后续处理。</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <p>暂无解析结果</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default ParseFileModule;
