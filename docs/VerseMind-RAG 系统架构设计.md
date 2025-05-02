# VerseMind-RAG 系统架构设计

## 1. 系统概述

VerseMind-RAG是一个文档智能处理与语义生成系统，主题为"Where Poetry Meets AI"。该系统支持文档加载、分块、解析、向量嵌入、索引、语义搜索和文本生成等功能，旨在提供一个完整的RAG（检索增强生成）解决方案。

## 2. 系统架构

### 2.1 整体架构

系统采用前后端分离架构：
- **前端**：React + Vite + TailwindCSS
- **后端**：FastAPI + Python服务
- **存储**：文件系统（文档存储）+ 向量数据库（FAISS/Chroma）
- **模型**：Ollama本地模型（优先）+ DeepSeek/OpenAI API

```
┌─────────────────┐      ┌─────────────────────────────────┐
│                 │      │                                 │
│  前端应用       │◄────►│  FastAPI后端                    │
│  React + Vite   │      │                                 │
│                 │      │  ┌─────────────┐ ┌────────────┐ │
└─────────────────┘      │  │文档处理服务 │ │向量处理服务│ │
                         │  └─────────────┘ └────────────┘ │
                         │                                 │
                         │  ┌─────────────┐ ┌────────────┐ │
                         │  │语义搜索服务 │ │文本生成服务│ │
                         │  └─────────────┘ └────────────┘ │
                         └───────────┬─────────────────────┘
                                     │
                         ┌───────────▼─────────────────────┐
                         │                                 │
                         │  Ollama / DeepSeek / OpenAI    │
                         │                                 │
                         └───────────┬─────────────────────┘
                                     │
                         ┌───────────▼─────────────────────┐
                         │                                 │
                         │  FAISS / Chroma                │
                         │                                 │
                         └─────────────────────────────────┘
```

### 2.2 数据流

1. 用户上传文档 → 文档加载服务解析 → 存储原始文档和元数据
2. 文档分块 → 文档解析 → 生成结构化内容
3. 结构化内容 → 向量嵌入 → 存入向量数据库
4. 用户查询 → 向量化查询 → 在向量数据库中检索相似内容
5. 检索结果 + 用户查询 → 文本生成服务 → 生成回答

## 3. 前端设计

### 3.1 页面结构

```
┌────────────────────────────────────────────────────────────┐
│ 导航栏 (顶部)                                   语言切换    │
├────────┬───────────────────────────────────────────────────┤
│        │                                                   │
│        │                                                   │
│        │                                                   │
│        │                                                   │
│ 功能   │                主交互区                           │
│ 导航栏 │                                                   │
│ (左侧) │                                                   │
│        │                                                   │
│        │                                                   │
│        │                                                   │
│        │                                                   │
└────────┴───────────────────────────────────────────────────┘
```

### 3.2 组件结构

```
App
├── Header
│   ├── Logo
│   └── LanguageSelector
├── Sidebar
│   ├── NavItem (LoadFile)
│   ├── NavItem (ChunkFile)
│   ├── NavItem (ParseFile)
│   ├── NavItem (EmbeddingFile)
│   ├── NavItem (IndexingWithVectorDB)
│   ├── NavItem (SimilaritySearch)
│   └── NavItem (Generation)
└── MainContent
    ├── LoadFileModule
    ├── ChunkFileModule
    ├── ParseFileModule
    ├── EmbeddingFileModule
    ├── IndexingModule
    ├── SearchModule
    └── GenerationModule
```

### 3.3 状态管理

使用React Context API和Hooks管理全局状态：
- 当前活动模块
- 处理中的文档
- 处理结果
- 用户配置（语言、模型选择等）

## 4. 后端设计

### 4.1 API结构

```
/api
├── /documents
│   ├── POST /upload - 上传文档
│   ├── GET /list - 获取文档列表
│   └── GET /{id} - 获取文档详情
├── /chunks
│   ├── POST /create - 创建文档分块
│   └── GET /{document_id} - 获取文档分块
├── /parse
│   └── POST /{document_id} - 解析文档
├── /embeddings
│   ├── POST /create - 创建嵌入
│   └── GET /models - 获取可用嵌入模型
├── /index
│   ├── POST /create - 创建索引
│   ├── GET /list - 获取索引列表
│   └── PUT /{id} - 更新索引
├── /search
│   └── POST /{index_id} - 执行语义搜索
└── /generate
    ├── POST /text - 生成文本
    └── GET /models - 获取可用生成模型
```

### 4.2 服务模块

```
services/
├── load_service.py - 文档加载服务
├── chunk_service.py - 文档分块服务
├── parse_service.py - 文档解析服务
├── embed_service.py - 向量嵌入服务
├── index_service.py - 向量索引服务
├── search_service.py - 语义搜索服务
└── generate_service.py - 文本生成服务
```

### 4.3 数据模型

```
models/
├── document.py - 文档模型
├── chunk.py - 文档分块模型
├── embedding.py - 嵌入模型
├── index.py - 索引模型
├── search.py - 搜索模型
└── generation.py - 生成模型
```

## 5. 存储设计

### 5.1 文件存储

```
storage/
├── documents/ - 原始文档
├── chunks/ - 文档分块
├── embeddings/ - 嵌入结果
├── indices/ - 索引数据
└── results/ - 生成结果
```

### 5.2 向量数据库

- **FAISS**：用于高效相似性搜索
- **Chroma**：用于元数据丰富的向量存储

## 6. 模型集成

### 6.1 嵌入模型

- **Ollama**：BGE-large（优先）
- **DeepSeek**：API集成
- **OpenAI**：API集成

### 6.2 生成模型

- **Ollama**：
  - llama3
  - gemma3:4b
  - deepseek-r1:14b
  - phi4
  - llava:v1.6
  - wizard-math
  - qwen2.5:7b
  - wizardcoder
  - openhermes
  - mistral
  - llama3.2-vision
  - codellama

## 7. 部署架构

### 7.1 本地开发环境

```
┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │
│  前端应用       │◄────►│  FastAPI后端    │
│  (localhost:3200)│      │ (localhost:8200)│
│                 │      │                 │
└─────────────────┘      └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │                 │
                         │  Ollama服务     │
                         │ (localhost:11434)│
                         │                 │
                         └─────────────────┘
```

### 7.2 Docker容器

```
┌─────────────────────────────────────────────────┐
│ Docker Network                                  │
│                                                 │
│ ┌─────────────┐      ┌─────────────┐           │
│ │             │      │             │           │
│ │  前端容器   │◄────►│  后端容器   │           │
│ │             │      │             │           │
│ └─────────────┘      └──────┬──────┘           │
│                             │                  │
│                      ┌──────▼──────┐           │
│                      │             │           │
│                      │ Ollama容器  │           │
│                      │             │           │
│                      └─────────────┘           │
│                                                 │
└─────────────────────────────────────────────────┘
```

## 8. 安全考虑

- 文件上传验证和限制
- API请求验证
- 敏感信息处理（如API密钥）
- 错误处理和日志记录

## 9. 扩展性考虑

- 模块化设计，便于添加新功能
- 支持多种模型和向量数据库
- 配置驱动的架构，便于调整参数
- 版本控制和命名空间支持
