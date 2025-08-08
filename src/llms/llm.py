from pathlib import Path
from typing import Any, Dict
import os
import httpx

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_deepseek import ChatDeepSeek
from typing import get_args

from src.config import load_yaml_config
from src.config.agents import LLMType

_llm_cache: dict[LLMType, BaseChatModel] = {}

def _get_config_file_path() -> str:
    #"获取config.yaml的绝对地址"
    return str((Path(__file__).parent.parent.parent / "conf.yaml").resolve())

def _get_llm_type_config_keys() -> dict[str, str]:
    #"建立LLM类型与config关键字的映射关系"
    return {
        "reasoning": "REASONING_MODEL",
        "basic": "BASIC_MODEL",
        "vision": "VISION_MODEL",
    }
    
def _get_env_llm_conf(llm_type: str) -> Dict[str, Any]:
    #"从conf.yaml里的BASIC_MODEL__api_key, BASIC_MODEL__base——url里返回一个conf字典"
    prefix = f"{llm_type.upper()}_MODEL__"
    conf = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            conf_key = key[len(prefix) :].lower()
            conf[conf_key] = value
    return conf

def _create_llm_use_conf(llm_type: LLMType, conf: Dict[str, Any]) -> BaseChatModel:
    #"从conf.yaml里创建一个LLM实例"
    llm_type_config_keys = _get_llm_type_config_keys()
    config_key = llm_type_config_keys.get(llm_type)
    
    if not config_key:
        raise ValueError(f"LLM type is unknown: {llm_type}")
    
    llm_conf = conf.get(config_key, {})
    if not isinstance(llm_conf, dict):
        raise ValueError(f"LLM configuration is invalid {llm_type}: {llm_conf}")
    
    env_conf = _get_env_llm_conf(llm_type)
    
    merged_conf = {**llm_conf, **env_conf}
    
    if not merged_conf:
        raise ValueError(f"There's no LLM configuration: {llm_type}")
    
    if "max_retries" not in merged_conf:
        merged_conf["max_retries"] = 3
        
    if llm_type == "reasoning":
        merged_conf["api_base"] = merged_conf.pop("base_url", None)
    
    verify_ssl = merged_conf.pop("verify_ssl", True)
    
    if not verify_ssl:
        http_client = httpx.Client(verify=False)
        http_async_client = httpx.AsyncClient(verify=False)
        merged_conf["http_client"] = http_client
        merged_conf["http_async_client"] = http_async_client
        
    if "azure_endpoint" in merged_conf or os.getenv("AZURE_OPENAI_ENDPOINT"):
        return AzureChatOpenAI(**merged_conf)
    
    if llm_type == "reasoning":
        return ChatDeepSeek(**merged_conf)
    else:
        return ChatOpenAI(**merged_conf)
    
def get_llm_by_type(llm_type: LLMType,) -> BaseChatModel:
    #"根据不同的type获取LLM实例"
    if llm_type in _llm_cache:
        return _llm_cache[llm_type]
    
    conf = load_yaml_config(_get_config_file_path())
    llm = _create_llm_use_conf(llm_type, conf)
    _llm_cache[llm_type] = llm
    return llm

def get_configured_llm_models() -> dict[str, list[str]]:
    #"获取conf.yaml里的所有LLM并生成字典映射"
    try: 
        conf = load_yaml_config(_get_config_file_path())
        llm_type_config_keys = _get_llm_type_config_keys()
        
        configured_models: dict[str, list[str]] = {}
        
        for llm_type in get_args(LLMType):
            config_key = llm_type_config_keys.get(llm_type, "")
            yaml_conf = conf.get(config_key, {}) if config_key else {}
            
            env_conf = _get_env_llm_conf(llm_type)
            
            merged_conf = {**yaml_conf, **env_conf}
            
            model_name = merged_conf.get("model")
            if model_name:
                configured_models.setdefault(llm_type, []).append(model_name)
        
        return configured_models
    
    except Exception as e:
        print(f"Warning: Failed to load LLM cofiguration: {e}")
        
    
    