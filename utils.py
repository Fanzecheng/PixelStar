import os
import json
import hashlib
import shutil
from pathlib import Path

def ensure_directory(path):
    """确保目录存在，不存在则创建"""
    os.makedirs(path, exist_ok=True)
    return path

def calculate_sha1(file_path):
    """计算文件的SHA1哈希值"""
    sha1 = hashlib.sha1()
    try:
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(65536)  # 64KB chunks
                if not data:
                    break
                sha1.update(data)
        return sha1.hexdigest()
    except IOError:
        return None

def read_json(file_path):
    """读取JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError):
        return None

def write_json(file_path, data):
    """写入JSON文件"""
    ensure_directory(os.path.dirname(file_path))
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_platform_natives_key():
    """获取当前平台的natives标识"""
    if os.name == 'nt':
        return 'natives-windows'
    elif os.name == 'posix':
        if os.uname().sysname == 'Darwin':
            return 'natives-macos'
        else:
            return 'natives-linux'
    return 'natives-unknown'