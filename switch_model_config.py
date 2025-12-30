#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型配置切换工具
"""

import os
import json
import shutil
import argparse

def switch_model_config(config_name):
    """
    切换模型配置
    :param config_name: 配置名称，如 "openai", "anthropic" 或 "example"
    """
    # 源配置文件路径
    source_config = f"model_config.{config_name}.json"
    
    # 目标配置文件路径
    target_config = "model_config.json"
    
    # 检查源配置文件是否存在
    if not os.path.exists(source_config):
        print(f"错误: 配置文件 {source_config} 不存在")
        return False
    
    try:
        # 备份当前配置
        if os.path.exists(target_config):
            backup_config = f"model_config.backup.{int(time.time())}.json"
            shutil.copy2(target_config, backup_config)
            print(f"当前配置已备份到 {backup_config}")
        
        # 复制新配置
        shutil.copy2(source_config, target_config)
        print(f"已切换到 {config_name} 配置")
        
        # 显示新配置内容
        with open(target_config, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        print("\n当前模型配置:")
        for model_type, model_config in config.items():
            print(f"\n{model_type}:")
            print(f"  名称: {model_config.get('name')}")
            print(f"  基础URL: {model_config.get('base_url')}")
            api_key = model_config.get('apikey', '')
            # 只显示API密钥的前4位和后4位，中间用星号代替
            if len(api_key) > 8:
                masked_key = f"{api_key[:4]}{'*' * (len(api_key) - 8)}{api_key[-4:]}"
            else:
                masked_key = '*' * len(api_key)
            print(f"  API密钥: {masked_key}")
        
        return True
        
    except Exception as e:
        print(f"切换配置失败: {e}")
        return False

def list_available_configs():
    """列出所有可用的配置"""
    configs = []
    
    # 查找所有 model_config.*.json 文件
    for file in os.listdir("."):
        if file.startswith("model_config.") and file.endswith(".json") and file != "model_config.json":
            config_name = file[12:-5]  # 提取中间部分作为配置名称
            configs.append(config_name)
    
    if not configs:
        print("没有找到可用的配置文件")
        return
    
    print("可用的配置:")
    for config in configs:
        print(f"  - {config}")

def show_current_config():
    """显示当前配置"""
    config_file = "model_config.json"
    
    if not os.path.exists(config_file):
        print("当前没有配置文件")
        return
    
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        print("\n当前模型配置:")
        for model_type, model_config in config.items():
            print(f"\n{model_type}:")
            print(f"  名称: {model_config.get('name')}")
            print(f"  基础URL: {model_config.get('base_url')}")
            
    except Exception as e:
        print(f"读取配置文件失败: {e}")

def main():
    parser = argparse.ArgumentParser(description="模型配置切换工具")
    parser.add_argument("action", choices=["switch", "list", "show"], help="操作类型")
    parser.add_argument("config", nargs="?", help="配置名称 (用于switch操作)")
    
    args = parser.parse_args()
    
    if args.action == "switch":
        if not args.config:
            print("错误: 切换配置需要指定配置名称")
            parser.print_help()
            return
        
        switch_model_config(args.config)
    elif args.action == "list":
        list_available_configs()
    elif args.action == "show":
        show_current_config()

if __name__ == "__main__":
    import time
    main()