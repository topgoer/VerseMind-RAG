import pytest
import os
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
        assert os.path.basename(service.chunks_dir) == "02-chunked-docs"
        assert os.path.basename(os.path.dirname(service.chunks_dir)) == "backend"

class TestParseService:
    """测试文档解析服务"""

    @patch('os.makedirs')
    def test_init(self, mock_makedirs):
        service = ParseService()
        assert service.chunks_dir == os.path.join(service.storage_dir, 'backend', '02-chunked-docs')

class TestEmbedService:
    """测试向量嵌入服务"""

    @patch('os.makedirs')
    def test_get_embedding_models(self, mock_makedirs):
        service = EmbedService()
        models = service.get_embedding_models()
        # Direct structure from config.toml matches your configuration
        assert "ollama" in models

class TestIndexService:
    """测试向量索引服务"""

    @patch('os.makedirs')
    def test_init(self, mock_makedirs):
        service = IndexService()
        # The path is now absolute, so we need to check the end of the path (basename) instead
        assert os.path.basename(os.path.dirname(service.indices_dir)) == "storage" and os.path.basename(service.indices_dir) == "indices"

class TestSearchService:
    """测试语义搜索服务"""

    @patch('os.makedirs')
    def test_init(self, mock_makedirs):
        service = SearchService()
        # Use absolute path to match actual implementation
        assert os.path.basename(service.results_dir) == os.path.basename("storage/results")

class TestGenerateService:
    """测试文本生成服务"""

    @patch('os.makedirs')
    def test_get_generation_models(self, mock_makedirs):
        service = GenerateService()
        models = service.get_generation_models()
        assert "model_groups" in models
        assert "ollama" in models["model_groups"]
