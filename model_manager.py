#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型管理器 - 用于管理视觉模型和分类模型
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from openai import OpenAI

class ModelManager:
    """模型管理器类，用于加载配置并管理不同类型的模型"""
    
    def __init__(self, config_path: str = "model_config.json"):
        """
        初始化模型管理器
        :param config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = None
        self.clients = {}  # 存储不同模型的客户端
        self.api_keys = {}  # 存储API密钥
        
        # 加载配置
        self.load_config()
        
        # 加载API密钥
        self.load_api_keys()
        
        # 初始化客户端
        self.init_clients()
    
    def load_config(self):
        """加载模型配置"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            else:
                raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        except Exception as e:
            logging.error(f"加载模型配置失败: {e}")
            raise
    
    def load_api_keys(self):
        """加载API密钥"""
        if not self.config:
            return
            
        # 从每个模型的配置中加载API密钥
        for model_type, model_config in self.config.items():
            api_key = model_config.get("apikey")
            if api_key:
                self.api_keys[model_type] = api_key
    
    def init_clients(self):
        """初始化模型客户端"""
        if not self.config:
            return
            
        for model_type, model_config in self.config.items():
            api_key = self.api_keys.get(model_type)
            if not api_key:
                logging.warning(f"模型 {model_type} 的API密钥未找到，跳过初始化")
                continue
                
            try:
                # 创建OpenAI客户端
                client = OpenAI(
                    api_key=api_key,
                    base_url=model_config.get("base_url")
                )
                self.clients[model_type] = client
            except Exception as e:
                logging.error(f"初始化模型 {model_type} 客户端失败: {e}")
    
    def get_client(self, model_type: str) -> Optional[OpenAI]:
        """
        获取指定类型的模型客户端
        :param model_type: 模型类型，如 "vision_model" 或 "classification_model"
        :return: OpenAI客户端实例
        """
        return self.clients.get(model_type)
    
    def get_model_config(self, model_type: str) -> Optional[Dict[str, Any]]:
        """
        获取指定类型的模型配置
        :param model_type: 模型类型
        :return: 模型配置字典
        """
        if not self.config:
            return None
        return self.config.get(model_type)
    
    def get_model_name(self, model_type: str) -> Optional[str]:
        """
        获取指定类型的模型名称
        :param model_type: 模型类型
        :return: 模型名称
        """
        model_config = self.get_model_config(model_type)
        if model_config:
            return model_config.get("name")
        return None
    
    def get_api_key(self, model_type: str) -> Optional[str]:
        """
        获取指定类型的模型API密钥
        :param model_type: 模型类型
        :return: API密钥
        """
        return self.api_keys.get(model_type)
    
    def reload_config(self):
        """重新加载配置"""
        self.config = None
        self.clients = {}
        self.api_keys = {}
        
        self.load_config()
        self.load_api_keys()
        self.init_clients()
    
    def update_model_config(self, model_type: str, new_config: Dict[str, Any]):
        """
        更新指定模型的配置
        :param model_type: 模型类型
        :param new_config: 新的配置
        """
        if not self.config:
            self.config = {}
            
        self.config[model_type] = new_config
        
        # 保存配置到文件
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"保存模型配置失败: {e}")
            return
            
        # 重新初始化客户端
        self.init_clients()
    
    def list_available_models(self) -> Dict[str, Dict[str, Any]]:
        """
        列出所有可用的模型
        :return: 模型信息字典
        """
        models = {}
        if not self.config:
            return models
            
        for model_type, model_config in self.config.items():
            models[model_type] = {
                "name": model_config.get("name"),
                "base_url": model_config.get("base_url"),
                "has_api_key": model_type in self.api_keys and self.api_keys[model_type] is not None,
                "client_initialized": model_type in self.clients
            }
            
        return models

# 全局模型管理器实例
_model_manager = None

def get_model_manager(config_path: str = "model_config.json") -> ModelManager:
    """
    获取全局模型管理器实例
    :param config_path: 配置文件路径
    :return: 模型管理器实例
    """
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager(config_path)
    return _model_manager