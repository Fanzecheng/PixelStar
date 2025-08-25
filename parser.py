import os
from urllib.parse import urljoin
from .utils import read_json, get_platform_natives_key


class VersionParser:
    def __init__(self, minecraft_dir):
        self.minecraft_dir = minecraft_dir
        self.versions_dir = os.path.join(minecraft_dir, 'versions')
        self.libraries_dir = os.path.join(minecraft_dir, 'libraries')
        self.assets_dir = os.path.join(minecraft_dir, 'assets')

    def get_version_manifest(self, manifest_url="https://piston-meta.mojang.com/mc/game/version_manifest.json"):
        """获取版本清单"""
        return read_json(manifest_url)  # 简化实现，实际应使用requests

    def get_version_json(self, version_id):
        """获取版本JSON数据"""
        version_path = os.path.join(self.versions_dir, version_id, f"{version_id}.json")
        return read_json(version_path)

    def parse_libraries(self, version_data):
        """解析库文件信息"""
        libraries = []
        natives_key = get_platform_natives_key()

        for lib in version_data.get('libraries', []):
            # 检查规则
            rules = lib.get('rules', [])
            if rules and not self._check_rules(rules):
                continue

            # 处理普通库
            downloads = lib.get('downloads', {})
            if 'artifact' in downloads:
                lib_info = {
                    'name': lib['name'],
                    'path': self._get_library_path(lib['name']),
                    'url': downloads['artifact'].get('url'),
                    'sha1': downloads['artifact'].get('sha1'),
                    'size': downloads['artifact'].get('size'),
                    'type': 'artifact'
                }
                libraries.append(lib_info)

            # 处理natives库
            classifiers = downloads.get('classifiers', {})
            if natives_key in classifiers:
                native_info = {
                    'name': lib['name'],
                    'path': self._get_natives_path(lib['name'], natives_key),
                    'url': classifiers[natives_key].get('url'),
                    'sha1': classifiers[natives_key].get('sha1'),
                    'size': classifiers[natives_key].get('size'),
                    'type': 'natives',
                    'extract': lib.get('extract')
                }
                libraries.append(native_info)

        return libraries

    def _get_library_path(self, name):
        """将库名称转换为路径"""
        parts = name.split(':')
        group, artifact, version = parts[0:3]
        group_path = group.replace('.', '/')
        filename = f"{artifact}-{version}.jar"
        return os.path.join(self.libraries_dir, group_path, artifact, version, filename)

    def _get_natives_path(self, name, natives_key):
        """获取natives库路径"""
        parts = name.split(':')
        group, artifact, version = parts[0:3]
        group_path = group.replace('.', '/')
        classifier = parts[3] if len(parts) > 3 else natives_key
        filename = f"{artifact}-{version}-{classifier}.jar"
        return os.path.join(self.libraries_dir, group_path, artifact, version, filename)

    def _check_rules(self, rules):
        """检查规则是否允许"""
        # 简化实现，实际需要解析OS和功能规则
        return True