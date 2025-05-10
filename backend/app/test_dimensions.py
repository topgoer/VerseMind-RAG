#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试BGE-M3向量维度修复
"""

import os
import json
import sys

def main():
    """检查嵌入文件中的向量维度"""
    if len(sys.argv) < 2:
        print("使用方法: python test_dimensions.py <嵌入文件路径>")
        sys.exit(1)
        
    embedding_file = sys.argv[1]
    
    if not os.path.exists(embedding_file):
        print(f"错误: 文件 {embedding_file} 不存在")
        sys.exit(1)
    
    print(f"正在分析嵌入文件: {embedding_file}")
    
    try:
        with open(embedding_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 打印顶级键
        top_keys = list(data.keys())
        print(f"文件顶级键: {top_keys}")
        
        # 打印嵌入模型信息
        model = data.get('model', 'unknown')
        print(f"嵌入模型: {model}")
        
        # 检查是否包含embeddings
        if 'embeddings' in data and isinstance(data['embeddings'], list):
            embeddings = data['embeddings']
            embedding_count = len(embeddings)
            print(f"嵌入向量数量: {embedding_count}")
            
            # 检查第一个向量维度
            if embedding_count > 0 and 'vector' in embeddings[0]:
                vector = embeddings[0]['vector']
                dimensions = len(vector)
                print(f"向量维度: {dimensions}")
                
                # 特别检查BGE-M3模型
                if 'm3' in model.lower() and dimensions != 1024:
                    print(f"警告: 检测到BGE-M3模型但向量维度为 {dimensions}，应为1024")
                elif 'bge' in model.lower() and 'm3' not in model.lower() and dimensions != 384:
                    print(f"警告: 检测到非M3的BGE模型但向量维度为 {dimensions}，应为384")
                
                # 检查向量值范围
                min_val = min(vector)
                max_val = max(vector)
                print(f"向量值范围: [{min_val:.6f}, {max_val:.6f}]")
                
            else:
                print("错误: 找不到向量数据")
        else:
            print("错误: 找不到embeddings键或非列表类型")
    
    except json.JSONDecodeError:
        print("错误: 文件格式不正确，无法解析JSON")
    except Exception as e:
        print(f"出现错误: {str(e)}")

if __name__ == "__main__":
    main()
