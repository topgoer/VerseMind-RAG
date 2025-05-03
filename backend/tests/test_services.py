import pytest
from unittest.mock import patch, MagicMock
from app.services.load_service import LoadService
from app.services.chunk_service import ChunkService
from app.services.parse_service import ParseService
from app.services.embed_service import EmbedService
from app.services.index_service import IndexService
from app.services.search_service import SearchService
from app.services.generate_service import GenerateService

class TestLoadService:
    """测试文档加载服务"""
    
    @patch('os.path.getsize')
    @patch('builtins.open')
    @patch('os.makedirs')
    def test_load_document(self, mock_makedirs, mock_open, mock_getsize):
        # 设置模拟
        mock_getsize.return_value = 1024
        
        # 创建服务实例
        service = LoadService()
        
        # 模拟文件对象
        mock_file = MagicMock()
        mock_file.filename = "test.pdf"
        
        # 测试方法
        result = service.get_document_list()
        assert isinstance(result, list)

class TestChunkService:
    """测试文档分块服务"""
    
    @patch('os.makedirs')
    def test_init(self, mock_makedirs):
        service = ChunkService()
        assert service.chunks_dir == "storage/chunks"

class TestParseService:
    """测试文档解析服务"""
    
    @patch('os.makedirs')
    def test_init(self, mock_makedirs):
        service = ParseService()
        assert service.chunks_dir == "storage/chunks"

class TestEmbedService:
    """测试向量嵌入服务"""
    
    @patch('os.makedirs')
    def test_get_embedding_models(self, mock_makedirs):
        service = EmbedService()
        models = service.get_embedding_models()
        assert "model_groups" in models
        assert "ollama" in models["providers"]

class TestIndexService:
    """测试向量索引服务"""
    
    @patch('os.makedirs')
    def test_init(self, mock_makedirs):
        service = IndexService()
        assert service.indices_dir == "storage/indices"

class TestSearchService:
    """测试语义搜索服务"""
    
    @patch('os.makedirs')
    def test_init(self, mock_makedirs):
        service = SearchService()
        assert service.results_dir == "storage/results"

class TestGenerateService:
    """测试文本生成服务"""
    
    @patch('os.makedirs')
    def test_get_generation_models(self, mock_makedirs):
        service = GenerateService()
        models = service.get_generation_models()
        assert "providers" in models
        assert "ollama" in models["providers"]
