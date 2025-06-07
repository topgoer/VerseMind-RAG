# Milvus Docker 便携服务

本目录用于快速部署和管理 Milvus 向量数据库服务，适用于多个项目间的便携复用。

## 目录结构
- `docker-compose.yml`：Milvus、etcd、minio 的 Docker Compose 配置
- `volumes/`：数据持久化目录（自动生成）

## 快速使用
1. **启动 Milvus 服务**
   ```bash
   docker-compose up -d
   ```
   启动后，Milvus 服务默认监听 19530 端口。

2. **停止服务**
   ```bash
   docker-compose down
   ```

3. **数据持久化**
   - 所有 Milvus 数据均保存在 `volumes/` 子目录下。
   - 只要保留该目录，数据不会因容器重建而丢失。

4. **跨项目复用**
   - 可将整个 `milvus-docker` 文件夹复制到任意项目根目录。
   - 进入该目录后直接启动即可，无需重新配置。

5. **多项目共用建议**
   - 建议不同项目的 collection 命名加前缀区分（如 `project1_xxx`）。
   - 如需多个独立 Milvus 实例，可修改端口和卷路径。

## 端口说明
- 19530：Milvus gRPC/HTTP 服务端口
- 9091：Milvus 管理端口

## 依赖
- 需先安装 [Docker](https://www.docker.com/) 和 [Docker Compose](https://docs.docker.com/compose/)

---

如需更多高级用法（如备份、迁移、升级），请参考主项目文档或 Milvus 官方文档。
