import os
import yaml
from typing import Dict, Any

def replace_env_vars(value: str) -> str:
    #把环境变量替换为string value
    if not isinstance(value, str):
        return value
    if value.startswith("$"):  # 修复：startwith -> startswith
        env_var = value[1:]
        return os.getenv(env_var, env_var)
    return value

def process_dict(config: Dict[str, Any]) -> Dict[str, Any]:
    #"把环境变量变为字典"
    if not config:
        return {}
    result = {}
    for key, value in config.items():
        if isinstance(value, dict):
            result[key] = process_dict(value)
        elif isinstance(value, str):
            result[key] = replace_env_vars(value)
        else:
            result[key] = value
    return result

_config_cache: Dict[str, Dict[str, Any]] = {}

def load_yaml_config(file_path:str) -> Dict[str, Any]:
    #"加载config.yaml"
    if not os.path.exists(file_path):
        return {}
    
    if file_path in _config_cache:
        return _config_cache[file_path]
    
    with open(file_path, "r") as f:
        config = yaml.safe_load(f)
    processed_config = process_dict(config)
    
    _config_cache[file_path] = processed_config
    return processed_config
