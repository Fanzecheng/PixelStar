import os
import requests
import threading
from queue import Queue
from .utils import ensure_directory, calculate_sha1

class Downloader:
    def __init__(self, max_workers=5):
        self.max_workers = max_workers
        self.queue = Queue()
        self.failed_downloads = []

    def add_download(self, url, path, sha1=None, size=None, callback=None):
        """添加下载任务"""
        self.queue.put({
            'url': url,
            'path': path,
            'sha1': sha1,
            'size': size,
            'callback': callback
        })

    def start(self):
        """开始下载"""
        threads = []
        for _ in range(self.max_workers):
            thread = threading.Thread(target=self._download_worker)
            thread.daemon = True
            thread.start()
            threads.append(thread)

        self.queue.join()  # 等待所有任务完成
        return self.failed_downloads

    def _download_worker(self):
        """下载工作线程"""
        while True:
            task = self.queue.get()
            try:
                self._download_file(
                    task['url'],
                    task['path'],
                    task['sha1'],
                    task['size']
                )
                if task['callback']:
                    task['callback'](task['path'])
            except Exception as e:
                self.failed_downloads.append({
                    'url': task['url'],
                    'path': task['path'],
                    'error': str(e)
                })
            finally:
                self.queue.task_done()

    def _download_file(self, url, path, expected_sha1=None, expected_size=None):
        """下载单个文件"""
        # 如果文件已存在且验证通过，则跳过下载
        if os.path.exists(path):
            if expected_sha1 and calculate_sha1(path) == expected_sha1:
                return
            if expected_size and os.path.getsize(path) == expected_size:
                return

        ensure_directory(os.path.dirname(path))

        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        # 下载后验证
        if expected_sha1 and calculate_sha1(path) != expected_sha1:
            raise Exception(f"SHA1 mismatch for {path}")

        if expected_size and os.path.getsize(path) != expected_size:
            raise Exception(f"Size mismatch for {path}")