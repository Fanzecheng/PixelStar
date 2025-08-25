import os
import shutil
import subprocess
import tempfile
import zipfile
from .parser import VersionParser
from .downloader import Downloader
from .auth import MicrosoftAuth
from .utils import ensure_directory, get_platform_natives_key


class MinecraftLauncher:
    def __init__(self, minecraft_dir):
        self.minecraft_dir = minecraft_dir
        self.parser = VersionParser(minecraft_dir)
        self.downloader = Downloader()
        self.natives_dir = os.path.join(tempfile.gettempdir(), 'minecraft_natives')

    def prepare_version(self, version_id):
        """准备游戏版本"""
        # 获取版本信息
        version_data = self.parser.get_version_json(version_id)
        if not version_data:
            raise Exception(f"Version {version_id} not found")

        # 处理继承关系
        if 'inheritsFrom' in version_data:
            parent_version = self.prepare_version(version_data['inheritsFrom'])
            # 合并父版本数据（简化实现）
            version_data = {**parent_version, **version_data}

        # 下载库文件
        libraries = self.parser.parse_libraries(version_data)
        for lib in libraries:
            if lib['url']:
                self.downloader.add_download(
                    lib['url'],
                    lib['path'],
                    lib.get('sha1'),
                    lib.get('size')
                )

        # 下载资源文件
        self._prepare_assets(version_data)

        # 启动下载
        failed = self.downloader.start()
        if failed:
            print(f"Failed to download {len(failed)} files")

        # 提取natives库
        self._extract_natives(libraries)

        return version_data

    def _prepare_assets(self, version_data):
        """准备资源文件"""
        asset_index = version_data.get('assetIndex', {})
        if 'id' in asset_index and 'url' in asset_index:
            assets_dir = os.path.join(self.minecraft_dir, 'assets')
            index_file = os.path.join(assets_dir, 'indexes', f"{asset_index['id']}.json")

            # 下载资源索引
            self.downloader.add_download(asset_index['url'], index_file)

            # 下载资源对象（简化实现，实际需要解析索引文件）
            # ...

    def _extract_natives(self, libraries):
        """提取natives库"""
        ensure_directory(self.natives_dir)

        # 清理之前的natives
        for item in os.listdir(self.natives_dir):
            item_path = os.path.join(self.natives_dir, item)
            if os.path.isfile(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)

        # 提取所有natives库
        for lib in libraries:
            if lib['type'] == 'natives' and os.path.exists(lib['path']):
                with zipfile.ZipFile(lib['path'], 'r') as zip_ref:
                    zip_ref.extractall(self.natives_dir)

    def construct_launch_command(self, version_data, username, uuid, access_token,
                                 game_dir=None, width=854, height=480):
        """构建启动命令"""
        if game_dir is None:
            game_dir = self.minecraft_dir

        # 获取主类
        main_class = version_data.get('mainClass', 'net.minecraft.client.main.Main')

        # 构建JVM参数
        jvm_args = [
            f"-Xmx2G",
            f"-Djava.library.path={self.natives_dir}",
            f"-Dminecraft.client.jar={os.path.join(self.versions_dir, version_data['id'], f'{version_data["id"]}.jar')}",
            f"-Dminecraft.applet.TargetDirectory={game_dir}"
        ]

        # 添加自定义JVM参数
        if 'arguments' in version_data and 'jvm' in version_data['arguments']:
            for arg in version_data['arguments']['jvm']:
                if isinstance(arg, dict):
                    # 处理规则（简化实现）
                    continue
                jvm_args.append(arg)

        # 构建游戏参数
        game_args = [
            "--username", username,
            "--version", version_data['id'],
            "--gameDir", game_dir,
            "--assetsDir", os.path.join(self.minecraft_dir, 'assets'),
            "--assetIndex", version_data.get('assetIndex', {}).get('id', ''),
            "--uuid", uuid,
            "--accessToken", access_token,
            "--userType", "mojang",
            "--versionType", "release",
            "--width", str(width),
            "--height", str(height)
        ]

        # 添加自定义游戏参数
        if 'arguments' in version_data and 'game' in version_data['arguments']:
            for arg in version_data['arguments']['game']:
                if isinstance(arg, dict):
                    # 处理规则（简化实现）
                    continue
                game_args.append(arg)

        # 构建类路径
        classpath = self._construct_classpath(version_data)

        # 组合完整命令
        command = ["java"] + jvm_args + ["-cp", classpath, main_class] + game_args
        return command

    def _construct_classpath(self, version_data):
        """构建类路径"""
        libraries = self.parser.parse_libraries(version_data)
        classpath_items = []

        # 添加版本jar文件
        version_jar = os.path.join(
            self.versions_dir,
            version_data['id'],
            f"{version_data['id']}.jar"
        )
        if os.path.exists(version_jar):
            classpath_items.append(version_jar)

        # 添加所有普通库
        for lib in libraries:
            if lib['type'] == 'artifact' and os.path.exists(lib['path']):
                classpath_items.append(lib['path'])

        # 使用系统特定的分隔符
        if os.name == 'nt':  # Windows
            return ";".join(classpath_items)
        else:  # Unix-like
            return ":".join(classpath_items)

    def launch_game(self, command, cwd=None):
        """启动游戏"""
        if cwd is None:
            cwd = self.minecraft_dir

        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        # 实时输出游戏日志
        def output_reader(pipe, label):
            for line in pipe:
                print(f"[{label}] {line.strip()}")

        import threading
        stdout_thread = threading.Thread(target=output_reader, args=(process.stdout, "STDOUT"))
        stderr_thread = threading.Thread(target=output_reader, args=(process.stderr, "STDERR"))

        stdout_thread.start()
        stderr_thread.start()

        return process