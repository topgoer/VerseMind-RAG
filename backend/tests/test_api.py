import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    """测试根路由"""
    response = client.get("/")
    assert response.status_code == 200
    assert "欢迎使用VerseMind-RAG API" in response.json()["message"]

def test_documents_list():
    """测试文档列表接口"""
    response = client.get("/api/documents/list")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_embedding_models():
    """测试嵌入模型列表接口"""
    response = client.get("/api/embeddings/models")
    assert response.status_code == 200
    assert "providers" in response.json()
    assert "ollama" in response.json()["providers"]
    assert "openai" in response.json()["providers"]

def test_generation_models():
    """测试生成模型列表接口"""
    response = client.get("/api/generate/models")
    assert response.status_code == 200
    assert "providers" in response.json()
    assert "ollama" in response.json()["providers"]
    assert "openai" in response.json()["providers"]

def test_indices_list():
    """测试索引列表接口"""
    response = client.get("/api/index/list")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
