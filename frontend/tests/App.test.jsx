import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import App from '../src/App';

// 模拟fetch API
global.fetch = jest.fn();

// 重置模拟
beforeEach(() => {
  fetch.mockClear();
});

test('renders header with correct title', () => {
  // 模拟API响应
  fetch.mockImplementation(() => 
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve([])
    })
  );
  
  render(<App />);
  const headerElement = screen.getByText(/VerseMind-RAG/i);
  expect(headerElement).toBeInTheDocument();
});

test('sidebar contains all required modules', () => {
  // 模拟API响应
  fetch.mockImplementation(() => 
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve([])
    })
  );
  
  render(<App />);
  
  // 检查所有模块是否存在
  expect(screen.getByText(/文档加载/i)).toBeInTheDocument();
  expect(screen.getByText(/文档分块/i)).toBeInTheDocument();
  expect(screen.getByText(/文档解析/i)).toBeInTheDocument();
  expect(screen.getByText(/向量嵌入/i)).toBeInTheDocument();
  expect(screen.getByText(/向量索引/i)).toBeInTheDocument();
  expect(screen.getByText(/语义搜索/i)).toBeInTheDocument();
  expect(screen.getByText(/文本生成/i)).toBeInTheDocument();
});

test('fetches documents on initial load', async () => {
  // 模拟文档列表API响应
  const mockDocuments = [
    { id: 'doc1', filename: 'test.pdf', upload_time: '20250412_123456' }
  ];
  
  fetch.mockImplementation(() => 
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve(mockDocuments)
    })
  );
  
  render(<App />);
  
  // 验证fetch被调用
  expect(fetch).toHaveBeenCalledWith('http://localhost:8200/api/documents/list');
  
  // 等待文档列表加载
  await waitFor(() => {
    expect(fetch).toHaveBeenCalledTimes(2); // 文档列表和索引列表
  });
});

test('changes active module when sidebar item is clicked', () => {
  // 模拟API响应
  fetch.mockImplementation(() => 
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve([])
    })
  );
  
  render(<App />);
  
  // 点击"语义搜索"模块
  fireEvent.click(screen.getByText(/语义搜索/i));
  
  // 验证主内容区域已更新
  expect(screen.getByText(/执行语义搜索/i)).toBeInTheDocument();
});
