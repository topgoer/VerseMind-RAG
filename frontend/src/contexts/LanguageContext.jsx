import React, { createContext, useContext, useState } from 'react';

// 创建语言上下文
export const LanguageContext = createContext();

// 语言文本
export const translations = {
  en: {
    // 通用
    appTitle: 'VerseMind-RAG',
    appSlogan: 'Where Poetry Meets AI',
    copyright: '© 2025 VerseMind',
    providerLabel: 'Provider',
    modelLabel: 'Model',
    
    // 侧边栏模块
    modules: 'Modules',
    selectModule: 'Select a module to use',
    moduleLoad: 'Document Loading',
    moduleChunk: 'Document Chunking',
    moduleParse: 'Document Parsing',
    moduleEmbedding: 'Vector Embedding',
    moduleIndexing: 'Vector Indexing',
    moduleSearch: 'Semantic Search',
    moduleGenerate: 'Text Generation',
    moduleChat: 'Conversational Q&A',
    
    // 按钮和操作
    refresh: 'Refresh',
    refreshEmbeddings: 'Refresh Embeddings',
    forceRefresh: 'Force Refresh',
    refreshing: 'Refreshing...',
    loading: 'Loading...',
    processing: 'Processing...',
    noData: 'No data available',
    submit: 'Submit',
    cancel: 'Cancel',
    delete: 'Delete',
    selectEmbeddings: 'Select Embeddings',
    noEmbeddingsAvailable: 'No embeddings available',
    noEmbeddingsFound: 'No embeddings found. Try refreshing or go to the Vector Embedding page.',
    embeddingsNotLoadedError: 'Embeddings data is not available or invalid.',
    vectorEmbeddingsRequired: 'Vector Embeddings Required',
    beforeIndexingHelp: 'Before creating a vector index, you need to generate vector embeddings for your documents.',
    goToVectorEmbedding: 'Go to Vector Embedding',
    
    // 文档加载模块
    documentLoading: 'Document Loading',
    documentLoadingDesc: 'Upload documents to start processing. Supports PDF, DOCX, TXT, Markdown, and CSV formats.',
    dragDropFiles: 'Drag and drop files here, or',
    selectFiles: 'Select Files',
    maxFileSize: 'Maximum file size: 100MB',
    documentList: 'Document List',
    fileName: 'File Name',
    fileType: 'Type',
    fileSize: 'Size',
    uploadTime: 'Upload Time',
    pageCount: 'Pages',
    noDocuments: 'No documents',
    
    // 文档分块模块
    documentChunking: 'Document Chunking',
    chunkingDesc: 'Split documents into smaller text chunks for further processing.',
    selectDocument: '-- Select a document --',
    chunkingStrategy: 'Chunking Strategy',
    byCharacter: 'By Character Count',
    byParagraph: 'By Paragraph',
    byHeading: 'By Heading',
    chunkSize: 'Chunk Size (characters)',
    chunkSizeRecommended: 'Recommended: 1000-1500 characters',
    overlapSize: 'Overlap Size (characters)',
    overlapRecommended: 'Recommended: 10-20% of chunk size',
    startChunking: 'Start Chunking',
    chunkingResults: 'Chunking Results',
    strategy: 'Strategy',
    chunks: 'Chunks',
    noChunks: 'No chunking results',
    
    // 文档解析模块
    documentParsing: 'Document Parsing',
    parsingDesc: 'Analyze document structure, extract paragraphs, headings, tables and images.',
    parsingStrategy: 'Parsing Strategy',
    fullParsing: 'Full Parsing',
    pageParsing: 'Page-by-Page Parsing',
    headingParsing: 'Heading Structure Parsing',
    extractTables: 'Extract Tables',
    extractImages: 'Extract Images',
    startParsing: 'Start Parsing',
    parsingResults: 'Parsing Results',
    documentInfo: 'Document Information',
    contentStats: 'Content Statistics',
    documentId: 'Document ID:',
    parseId: 'Parse ID:',
    sectionCount: 'Sections:',
    paragraphCount: 'Paragraphs:',
    tableCount: 'Tables:',
    imageCount: 'Images:',
    parsingExample: 'Parsing Example',
    noParsing: 'No parsing results',
    
    // 向量嵌入模块
    vectorEmbedding: 'Vector Embedding',
    embeddingDesc: 'Convert text chunks into vector representations for retrieval.',
    embeddingProvider: 'Embedding Provider',
    embeddingModel: 'Embedding Model',
    dimensions: 'dimensions',
    generateEmbeddings: 'Generate Embeddings',
    embeddingResults: 'Embedding Results',
    embeddingInfo: 'Embedding Information',
    modelInfo: 'Model Information',
    embeddingId: 'Embedding ID:',
    timestamp: 'Timestamp:',
    provider: 'Provider:',
    model: 'Model:',
    dimensionCount: 'Dimensions:',
    statsInfo: 'Statistics',
    vectorCount: 'Total Vectors:',
    resultFile: 'Result File:',
    vectorExample: 'Vector Example',
    noEmbeddings: 'No embedding results',
    
    // 向量索引模块
    vectorIndexing: 'Vector Indexing',
    indexingDesc: 'Create vector indices for efficient retrieval.',
    vectorDatabase: 'Vector Database',
    collectionName: 'Collection Name',
    collectionPlaceholder: 'e.g., finance_documents',
    indexName: 'Index Name',
    indexPlaceholder: 'e.g., quarterly_reports',
    createIndex: 'Create Index',
    indexList: 'Index List',
    indexId: 'Index ID',
    version: 'Version',
    vectors: 'Vectors',
    noIndices: 'No indices',
    
    // 语义搜索模块
    semanticSearch: 'Semantic Search',
    searchDesc: 'Perform precise retrieval based on vector similarity.',
    selectIndex: '-- Select an index --',
    queryText: 'Query Text',
    queryPlaceholder: 'Enter your question or query...',
    resultCount: 'Result Count',
    similarityThreshold: 'Similarity Threshold',
    minCharacters: 'Min Characters',
    performSearch: 'Perform Search',
    searchResults: 'Search Results',
    queryInfo: 'Query Information',
    searchId: 'Search ID:',
    documentFilename: 'Document:',
    documentSource: 'Source Document:',
    documentReference: 'Document Reference:',
    documentContext: 'Document Context',
    usingDocumentContext: 'Using Document Context',
    searchIdLabel: 'Search ID',
    searchCompleted: 'Search Completed',
    noDocumentContext: 'No Document Context',
    relatedText: 'Related Text',
    result: 'Result',
    similarity: 'Similarity:',
    source: 'Source:',
    noResults: 'No results found',
    enterQuery: 'Please enter a query and perform search',
    
    // 文本生成模块
    textGeneration: 'Text Generation',
    generationDesc: 'Generate coherent, relevant responses based on retrieval results.',
    usingSearchResults: 'Using recent search results',
    query: 'Query:',
    foundResults: 'Found',
    relevantResults: 'relevant results',
    promptText: 'Prompt Text',
    promptPlaceholder: 'Enter your prompt, e.g., Summarize the main points from these documents...',
    generationProvider: 'Generation Provider',
    generationModel: 'Generation Model',
    temperature: 'Temperature',
    precise: 'Precise',
    creative: 'Creative',
    maxTokens: 'Max Tokens',
    generateText: 'Generate Text',
    generationResults: 'Generation Results',
    generationInfo: 'Generation Information',
    generationId: 'Generation ID:',
    prompt: 'Prompt:',
    generatedText: 'Generated Text',
    noGeneration: 'Please enter a prompt and generate text',
    
    // 对话式问答模块
    conversationalQA: 'Conversational Q&A',
    chatDesc: 'Ask questions and get answers based on your documents using natural language.',
    selectModel: 'Select Model',
    askQuestion: 'Ask a question or request a task...',
    chatPlaceholder: 'Type your message here...',
    send: 'Send',
    sending: 'Sending...',
    thinking: 'Thinking...',
    references: 'References',
    messagesCount: '{count} messages',
    startConversation: 'Start a conversation',
    welcomeMessage: 'Welcome to VerseMind-RAG! Select an index and ask questions about your documents. You can also request tasks like "extract page 5 and generate a summary".',
    selectIndexFirst: 'Please select an index first',
    chatError: 'An error occurred while processing your request',
    
    // 任务型请求
    taskDetected: 'I detected the following tasks:',
    taskPromptPrefix: 'Please perform the following tasks based on the document:',
    taskExtractPage: 'Extract content from page {page}',
    taskSummarize: 'Generate a summary of the content',
    taskCompare: 'Compare the information',
    taskFind: 'Find specific information',
    taskAnalyze: 'Analyze the content',
    
    // 语言切换
    language: 'Language',
    switchToChinese: '中文',
    switchToEnglish: 'English',
    
    // 错误信息
    error: 'Error',
    uploadFailed: 'Upload failed',
    chunkingFailed: 'Chunking failed',
    parsingFailed: 'Parsing failed',
    embeddingFailed: 'Embedding failed',
    indexingFailed: 'Indexing failed',
    searchFailed: 'Search failed',
    generationFailed: 'Generation failed',
    deleteFailed: 'Delete failed',
    confirmDeleteTitle: 'Confirm Deletion',
    confirmDeleteMessage: 'Are you sure you want to delete {item}? This action cannot be undone.'
  },
  zh: {
    // 通用
    appTitle: 'VerseMind-RAG',
    appSlogan: '诗意与智慧的交融',
    copyright: '© 2025 VerseMind',
    providerLabel: '提供商',
    modelLabel: '模型',
    
    // 侧边栏模块
    modules: '功能模块',
    selectModule: '选择要使用的模块',
    moduleLoad: '文档加载',
    moduleChunk: '文档分块',
    moduleParse: '文档解析',
    moduleEmbedding: '向量嵌入',
    moduleIndexing: '向量索引',
    moduleSearch: '语义搜索',
    moduleGenerate: '文本生成',
    moduleChat: '对话式问答',
    
    // 按钮和操作
    refresh: '刷新',
    refreshEmbeddings: '刷新嵌入',
    forceRefresh: '强制刷新',
    refreshing: '刷新中...',
    loading: '加载中...',
    processing: '处理中...',
    noData: '暂无数据',
    submit: '提交',
    cancel: '取消',
    delete: '删除',
    selectEmbeddings: '选择嵌入',
    noEmbeddingsAvailable: '没有可用的嵌入',
    noEmbeddingsFound: '未找到嵌入。请尝试刷新或前往向量嵌入页面创建嵌入。',
    embeddingsNotLoadedError: '嵌入数据不可用或无效。',
    vectorEmbeddingsRequired: '需要向量嵌入',
    beforeIndexingHelp: '在创建向量索引之前，您需要为文档生成向量嵌入。',
    goToVectorEmbedding: '前往向量嵌入页面',
    
    // 文档加载模块
    documentLoading: '文档加载',
    documentLoadingDesc: '上传文档以开始处理。支持PDF、DOCX、TXT、Markdown和CSV格式。',
    dragDropFiles: '拖放文件到此处，或',
    selectFiles: '选择文件',
    maxFileSize: '最大文件大小: 100MB',
    documentList: '文档列表',
    fileName: '文件名',
    fileType: '类型',
    fileSize: '大小',
    uploadTime: '上传时间',
    pageCount: '页数',
    noDocuments: '暂无文档',
    
    // 文档分块模块
    documentChunking: '文档分块',
    chunkingDesc: '将文档分割成较小的文本块，以便于后续处理。',
    selectDocument: '-- 请选择文档 --',
    chunkingStrategy: '分块策略',
    byCharacter: '按字符数',
    byParagraph: '按段落',
    byHeading: '按标题',
    chunkSize: '块大小（字符数）',
    chunkSizeRecommended: '建议值：1000-1500字符',
    overlapSize: '重叠大小（字符数）',
    overlapRecommended: '建议值：块大小的10-20%',
    startChunking: '开始分块',
    chunkingResults: '分块结果',
    strategy: '策略',
    chunks: '块数量',
    noChunks: '暂无分块结果',
    
    // 文档解析模块
    documentParsing: '文档解析',
    parsingDesc: '分析文档结构，提取段落、标题、表格和图像。',
    parsingStrategy: '解析策略',
    fullParsing: '全文解析',
    pageParsing: '分页解析',
    headingParsing: '标题结构解析',
    extractTables: '提取表格',
    extractImages: '提取图像',
    startParsing: '开始解析',
    parsingResults: '解析结果',
    documentInfo: '文档信息',
    contentStats: '内容统计',
    documentId: '文档ID:',
    parseId: '解析ID:',
    sectionCount: '章节数:',
    paragraphCount: '段落数:',
    tableCount: '表格数:',
    imageCount: '图像数:',
    parsingExample: '解析示例',
    noParsing: '暂无解析结果',
    
    // 向量嵌入模块
    vectorEmbedding: '向量嵌入',
    embeddingDesc: '将文本块转换为向量表示，以便于后续检索。',
    embeddingProvider: '嵌入提供商',
    embeddingModel: '嵌入模型',
    dimensions: '维度',
    generateEmbeddings: '生成嵌入',
    embeddingResults: '嵌入结果',
    embeddingInfo: '嵌入信息',
    modelInfo: '模型信息',
    embeddingId: '嵌入ID:',
    timestamp: '时间戳:',
    provider: '提供商:',
    model: '模型:',
    dimensionCount: '维度:',
    statsInfo: '统计信息',
    vectorCount: '向量总数:',
    resultFile: '结果文件:',
    vectorExample: '向量示例',
    noEmbeddings: '暂无嵌入结果',
    
    // 向量索引模块
    vectorIndexing: '向量索引',
    indexingDesc: '创建向量索引以支持高效检索。',
    vectorDatabase: '向量数据库',
    collectionName: '集合名称',
    collectionPlaceholder: '例如：finance_documents',
    indexName: '索引名称',
    indexPlaceholder: '例如：quarterly_reports',
    createIndex: '创建索引',
    indexList: '索引列表',
    indexId: '索引ID',
    version: '版本',
    vectors: '向量数',
    noIndices: '暂无索引',
    
    // 语义搜索模块
    semanticSearch: '语义搜索',
    searchDesc: '基于向量相似度进行精准检索。',
    selectIndex: '-- 请选择索引 --',
    queryText: '查询文本',
    queryPlaceholder: '输入您的问题或查询...',
    resultCount: '返回结果数量',
    similarityThreshold: '相似度阈值',
    minCharacters: '最小字符数',
    performSearch: '执行搜索',
    searchResults: '搜索结果',
    queryInfo: '查询信息',
    searchId: '搜索ID:',
    documentFilename: '文档:',
    documentSource: '源文档:',
    documentReference: '文档引用:',
    documentContext: '文档上下文',
    usingDocumentContext: '使用文档上下文',
    searchIdLabel: '搜索ID',
    searchCompleted: '搜索完成',
    noDocumentContext: '无文档上下文',
    relatedText: '相关文本',
    result: '结果',
    similarity: '相似度:',
    source: '来源:',
    noResults: '未找到相关结果',
    enterQuery: '请输入查询并执行搜索',
    
    // 文本生成模块
    textGeneration: '文本生成',
    generationDesc: '基于检索结果生成连贯、相关的回答。',
    usingSearchResults: '使用最近的搜索结果',
    query: '查询:',
    foundResults: '找到',
    relevantResults: '个相关结果',
    promptText: '提示文本',
    promptPlaceholder: '输入您的提示，例如：总结这些文档的主要观点...',
    generationProvider: '生成提供商',
    generationModel: '生成模型',
    temperature: '温度',
    precise: '精确',
    creative: '创意',
    maxTokens: '最大令牌数',
    generateText: '生成文本',
    generationResults: '生成结果',
    generationInfo: '生成信息',
    generationId: '生成ID:',
    prompt: '提示:',
    generatedText: '生成文本',
    noGeneration: '请输入提示并生成文本',
    
    // 对话式问答模块
    conversationalQA: '对话式问答',
    chatDesc: '使用自然语言提问，基于您的文档获取回答。',
    selectModel: '选择模型',
    askQuestion: '输入问题或请求任务...',
    chatPlaceholder: '在此输入您的消息...',
    send: '发送',
    sending: '发送中...',
    thinking: '思考中...',
    references: '引用来源',
    messagesCount: '{count}条消息',
    startConversation: '开始对话',
    welcomeMessage: '欢迎使用VerseMind-RAG！请选择一个索引，然后提问关于您文档的问题。您也可以请求执行任务，如"提取第5页并生成摘要"。',
    selectIndexFirst: '请先选择一个索引',
    chatError: '处理您的请求时发生错误',
    
    // 任务型请求
    taskDetected: '我检测到以下任务：',
    taskPromptPrefix: '请基于文档执行以下任务：',
    taskExtractPage: '提取第{page}页的内容',
    taskSummarize: '生成内容摘要',
    taskCompare: '比较信息',
    taskFind: '查找特定信息',
    taskAnalyze: '分析内容',
    
    // 语言切换
    language: '语言',
    switchToChinese: '中文',
    switchToEnglish: 'English',
    
    // 错误信息
    error: '错误',
    uploadFailed: '上传失败',
    chunkingFailed: '分块失败',
    parsingFailed: '解析失败',
    embeddingFailed: '嵌入失败',
    indexingFailed: '索引失败',
    searchFailed: '搜索失败',
    generationFailed: '生成失败',
    deleteFailed: '删除失败',
    confirmDeleteTitle: '确认删除',
    confirmDeleteMessage: '您确定要删除 {item} 吗？此操作无法撤销。'
  }
};

// 语言提供者组件
export const LanguageProvider = ({ children }) => {
  const [language, setLanguage] = useState('en');
  
  const toggleLanguage = () => {
    setLanguage(language === 'en' ? 'zh' : 'en');
  };
  
  const t = (key, params = {}) => {
    let text = translations[language][key] || key;
    
    // 处理参数替换
    if (params) {
      Object.keys(params).forEach(param => {
        text = text.replace(`{${param}}`, params[param]);
      });
    }
    
    return text;
  };
  
  return (
    <LanguageContext.Provider value={{ language, toggleLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

// 自定义钩子，方便在组件中使用
export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};

