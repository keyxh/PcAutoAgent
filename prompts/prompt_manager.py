#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG Prompt管理器
用于动态检索和管理不同平台、系统的专用prompt
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class PromptManager:
    """RAG Prompt管理器"""
    
    def __init__(self, prompts_dir: str = None):
        """
        初始化Prompt管理器
        :param prompts_dir: prompts目录路径，默认为当前目录下的prompts文件夹
        """
        if prompts_dir is None:
            prompts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts')
        
        self.prompts_dir = Path(prompts_dir)
        self.applicants_dir = self.prompts_dir / 'applicants'
        self.systems_dir = self.prompts_dir / 'systems'
        
        # 确保目录存在
        self.applicants_dir.mkdir(exist_ok=True)
        self.systems_dir.mkdir(exist_ok=True)
        
        # 加载所有prompt缓存
        self.applicant_prompts = {}
        self.system_prompts = {}
        self.applicant_index = {}
        self.system_index = {}
        
        self._load_all_prompts()
        logging.info(f"Prompt管理器初始化完成，应用数量: {len(self.applicant_prompts)}, 系统数量: {len(self.system_prompts)}")
    
    def _load_all_prompts(self):
        """加载所有prompt文件"""
        self._load_applicant_prompts()
        self._load_system_prompts()
    
    def _load_applicant_prompts(self):
        """加载应用专用prompt"""
        for applicant_file in self.applicants_dir.glob('*.json'):
            try:
                with open(applicant_file, 'r', encoding='utf-8') as f:
                    applicant_data = json.load(f)
                    applicant_name = applicant_file.stem
                    self.applicant_prompts[applicant_name] = applicant_data
                    
                    # 构建索引
                    self._build_applicant_index(applicant_name, applicant_data)
                    
                logging.info(f"加载应用prompt: {applicant_name}")
            except Exception as e:
                logging.error(f"加载应用prompt失败 {applicant_file}: {e}")
    
    def _load_system_prompts(self):
        """加载系统专用prompt"""
        for system_file in self.systems_dir.glob('*.json'):
            try:
                with open(system_file, 'r', encoding='utf-8') as f:
                    system_data = json.load(f)
                    system_name = system_file.stem
                    self.system_prompts[system_name] = system_data
                    
                    # 构建索引
                    self._build_system_index(system_name, system_data)
                    
                logging.info(f"加载系统prompt: {system_name}")
            except Exception as e:
                logging.error(f"加载系统prompt失败 {system_file}: {e}")
    
    def _build_applicant_index(self, applicant_name: str, applicant_data: Dict):
        """构建应用prompt索引"""
        if 'keywords' not in applicant_data:
            return
            
        for keyword in applicant_data['keywords']:
            if keyword not in self.applicant_index:
                self.applicant_index[keyword] = []
            self.applicant_index[keyword].append(applicant_name)
    
    def _build_system_index(self, system_name: str, system_data: Dict):
        """构建系统prompt索引"""
        if 'keywords' not in system_data:
            return
            
        for keyword in system_data['keywords']:
            if keyword not in self.system_index:
                self.system_index[keyword] = []
            self.system_index[keyword].append(system_name)
    
    def get_applicant_prompt(self, applicant_name: str) -> Optional[str]:
        """
        获取指定应用的prompt
        :param applicant_name: 应用名称
        :return: 应用prompt文本或None
        """
        if applicant_name in self.applicant_prompts:
            return self.applicant_prompts[applicant_name].get('prompt', '')
        return None
    
    def get_system_prompt(self, system_name: str) -> Optional[str]:
        """
        获取指定系统的prompt
        :param system_name: 系统名称
        :return: 系统prompt文本或None
        """
        if system_name in self.system_prompts:
            return self.system_prompts[system_name].get('prompt', '')
        return None
    
    def search_applicant_prompts(self, keywords: List[str]) -> List[Tuple[str, str]]:
        """
        搜索相关应用prompt
        :param keywords: 关键词列表
        :return: [(applicant_name, prompt), ...]
        """
        results = []
        for keyword in keywords:
            if keyword in self.applicant_index:
                for applicant_name in self.applicant_index[keyword]:
                    if applicant_name not in [r[0] for r in results]:  # 避免重复
                        prompt = self.get_applicant_prompt(applicant_name)
                        if prompt:
                            results.append((applicant_name, prompt))
        return results
    
    def search_system_prompts(self, keywords: List[str]) -> List[Tuple[str, str]]:
        """
        搜索相关系统prompt
        :param keywords: 关键词列表
        :return: [(system_name, prompt), ...]
        """
        results = []
        for keyword in keywords:
            if keyword in self.system_index:
                for system_name in self.system_index[keyword]:
                    if system_name not in [r[0] for r in results]:  # 避免重复
                        prompt = self.get_system_prompt(system_name)
                        if prompt:
                            results.append((system_name, prompt))
        return results
    
    def get_combined_prompt(self, platform_keywords: List[str] = None, 
                          system_keywords: List[str] = None,
                          base_prompt: str = None) -> str:
        """
        获取组合的prompt（基础prompt + 应用相关 + 系统相关）
        :param platform_keywords: 应用关键词
        :param system_keywords: 系统关键词
        :param base_prompt: 基础prompt
        :return: 组合后的prompt文本
        """
        combined_parts = []
        
        # 添加基础prompt
        if base_prompt:
            combined_parts.append(base_prompt)
        
        # 添加应用相关prompt
        if platform_keywords:
            applicant_prompts = self.search_applicant_prompts(platform_keywords)
            for applicant_name, applicant_prompt in applicant_prompts:
                combined_parts.append(f"\n\n=== {applicant_name.upper()} 应用专用操作指南 ===")
                combined_parts.append(applicant_prompt)
        
        # 添加系统相关prompt
        if system_keywords:
            system_prompts = self.search_system_prompts(system_keywords)
            for system_name, system_prompt in system_prompts:
                combined_parts.append(f"\n\n=== {system_name.upper()} 系统专用操作指南 ===")
                combined_parts.append(system_prompt)
        
        return "".join(combined_parts)
    
    def get_available_applicants(self) -> List[str]:
        """获取所有可用的应用列表"""
        return list(self.applicant_prompts.keys())
    
    def get_available_systems(self) -> List[str]:
        """获取所有可用的系统列表"""
        return list(self.system_prompts.keys())
    
    def get_applicant_info(self, applicant_name: str) -> Optional[Dict]:
        """获取应用详细信息"""
        return self.applicant_prompts.get(applicant_name)
    
    def get_system_info(self, system_name: str) -> Optional[Dict]:
        """获取系统详细信息"""
        return self.system_prompts.get(system_name)
    
    def add_applicant_prompt(self, applicant_name: str, prompt_data: Dict):
        """添加新的应用prompt"""
        try:
            applicant_file = self.applicants_dir / f"{applicant_name}.json"
            with open(applicant_file, 'w', encoding='utf-8') as f:
                json.dump(prompt_data, f, ensure_ascii=False, indent=2)
            
            # 重新加载
            self._load_applicant_prompts()
            logging.info(f"添加应用prompt: {applicant_name}")
        except Exception as e:
            logging.error(f"添加应用prompt失败 {applicant_name}: {e}")
            raise
    
    def add_system_prompt(self, system_name: str, prompt_data: Dict):
        """添加新的系统prompt"""
        try:
            system_file = self.systems_dir / f"{system_name}.json"
            with open(system_file, 'w', encoding='utf-8') as f:
                json.dump(prompt_data, f, ensure_ascii=False, indent=2)
            
            # 重新加载
            self._load_system_prompts()
            logging.info(f"添加系统prompt: {system_name}")
        except Exception as e:
            logging.error(f"添加系统prompt失败 {system_name}: {e}")
            raise


def get_prompt_manager() -> PromptManager:
    """获取全局PromptManager实例"""
    if not hasattr(get_prompt_manager, '_instance'):
        get_prompt_manager._instance = PromptManager()
    return get_prompt_manager._instance