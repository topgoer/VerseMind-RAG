import React, { useState, useEffect, useRef } from 'react';

const WechatDownloader = () => {
  const [biz, setBiz] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState(''); // 'success', 'error', 'info', 'progress'
  const [downloadedFiles, setDownloadedFiles] = useState([]);
  const pollIntervalRef = useRef(null);

  // 清理轮询
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  // 检查下载的文件
  const checkDownloadedFiles = async () => {
    try {
      const response = await fetch('/api/n8n/v1/n8n/recent-downloads?minutes=10');
      if (response.ok) {
        const recentFiles = await response.json();
        // recentFiles 直接是文档数组
        setDownloadedFiles(recentFiles);
        if (recentFiles.length > 0) {
          setMessage(`下载完成！共获取 ${recentFiles.length} 个文件`);
          setMessageType('success');
          setLoading(false);
          return true; // 返回true表示找到了文件
        }
      }
    } catch (error) {
      console.error('Error checking downloaded files:', error);
    }
    return false; // 返回false表示没有找到文件
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!biz.trim()) {
      setMessage('请输入有效的公众号biz参数');
      setMessageType('error');
      return;
    }

    setLoading(true);
    setMessage('正在启动下载任务...');
    setMessageType('progress');
    setDownloadedFiles([]);

    try {
      const response = await fetch('/api/n8n/v1/n8n/trigger-wechat-download', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ biz: biz.trim() }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setMessage('下载任务已启动，正在后台处理...');
        setMessageType('progress');
        setBiz(''); // 清空输入框
        
        // 开始轮询任务状态 - 暂时简化为定时检查文件
        setTimeout(async () => {
          const found = await checkDownloadedFiles();
          if (found) return; // 如果找到文件，就不继续轮询了
        }, 10000); // 10秒后开始检查文件

        // 继续检查文件，每15秒一次，最多检查5次
        let checkCount = 0;
        const maxChecks = 5;
        const checkInterval = setInterval(async () => {
          checkCount++;
          const found = await checkDownloadedFiles();
          
          if (found || checkCount >= maxChecks) {
            clearInterval(checkInterval);
            if (!found && downloadedFiles.length === 0) {
              setMessage('下载任务可能仍在进行中，请稍后手动刷新文档列表');
              setMessageType('info');
              setLoading(false);
            }
          }
        }, 15000);
      } else {
        setMessage(data.detail || data.message || '启动下载任务失败');
        setMessageType('error');
        setLoading(false);
      }
    } catch (error) {
      console.error('Error triggering download:', error);
      setMessage('网络错误，请检查连接后重试');
      setMessageType('error');
      setLoading(false);
    }
  };

  const getMessageStyle = () => {
    const baseStyle = 'mt-4 p-3 rounded-md text-sm';
    switch (messageType) {
      case 'success':
        return `${baseStyle} bg-green-100 text-green-700 border border-green-300`;
      case 'error':
        return `${baseStyle} bg-red-100 text-red-700 border border-red-300`;
      case 'info':
        return `${baseStyle} bg-blue-100 text-blue-700 border border-blue-300`;
      case 'progress':
        return `${baseStyle} bg-yellow-100 text-yellow-700 border border-yellow-300`;
      default:
        return baseStyle;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 max-w-md mx-auto">
      <h2 className="text-xl font-semibold text-gray-800 mb-4">
        微信公众号文章下载
      </h2>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="biz" className="block text-sm font-medium text-gray-700 mb-2">
            公众号 BIZ 参数
          </label>
          <input
            type="text"
            id="biz"
            value={biz}
            onChange={(e) => setBiz(e.target.value)}
            placeholder="请输入公众号的biz参数"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={loading}
          />
          <p className="mt-1 text-xs text-gray-500">
            biz参数可以从公众号文章链接中获取
          </p>
        </div>

        <button
          type="submit"
          disabled={loading || !biz.trim()}
          className={`w-full py-2 px-4 rounded-md font-medium transition-colors ${
            loading || !biz.trim()
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2'
          }`}
        >
          {loading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              启动中...
            </span>
          ) : (
            '开始下载'
          )}
        </button>
      </form>

      {message && (
        <div className={getMessageStyle()}>
          {messageType === 'progress' && (
            <div className="flex items-center">
              <svg className="animate-spin -ml-1 mr-3 h-4 w-4 text-yellow-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>{message}</span>
            </div>
          )}
          {messageType !== 'progress' && message}
        </div>
      )}

      {/* 下载文件列表 */}
      {downloadedFiles.length > 0 && (
        <div className="mt-4 p-3 bg-gray-50 rounded-md">
          <h4 className="text-sm font-medium text-gray-700 mb-2">已下载的文件：</h4>
          <ul className="space-y-1">
            {downloadedFiles.map((file, index) => (
              <li key={file.document_id || file.id || `file-${index}`} className="text-xs text-gray-600 flex items-center">
                <span className="w-2 h-2 bg-green-400 rounded-full mr-2"></span>
                {file.filename || file.name || `文件 ${index + 1}`}
                {file.size && <span className="ml-2 text-gray-500">({file.size})</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-6 text-xs text-gray-500">
        <p className="mb-2"><strong>使用说明：</strong></p>
        <ul className="list-disc list-inside space-y-1">
          <li>从公众号文章链接中复制biz参数</li>
          <li>点击"开始下载"启动后台下载任务</li>
          <li>下载完成后文件将保存到指定目录</li>
          <li>整个过程可能需要几分钟时间</li>
        </ul>
      </div>
    </div>
  );
};

export default WechatDownloader;

