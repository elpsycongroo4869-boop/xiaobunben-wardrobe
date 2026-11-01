"""不依赖外部包的图片文件存在性、基本结构与 SHA256 核验；不做语义识别。"""
import hashlib
from pathlib import Path


def fingerprint(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError('图片文件不存在')
    data = path.read_bytes()
    if len(data) < 1024:
        raise ValueError('图片文件过小，不能作为出图凭证')
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        if data[8:16] != b'\x00\x00\x00\rIHDR' or data[-12:] != b'\x00\x00\x00\x00IEND\xaeB`\x82':
            raise ValueError('PNG 文件缺少关键结构')
        width = int.from_bytes(data[16:20], 'big')
        height = int.from_bytes(data[20:24], 'big')
        if not (64 <= width <= 32768 and 64 <= height <= 32768):
            raise ValueError('PNG 图片尺寸异常')
    elif data[:3] == b'\xff\xd8\xff':
        if data[-2:] != b'\xff\xd9':
            raise ValueError('JPEG 文件不完整')
    elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        if int.from_bytes(data[4:8], 'little') + 8 != len(data):
            raise ValueError('WEBP 文件长度不一致')
    else:
        raise ValueError('无法识别 PNG/JPEG/WEBP 图片文件')
    return {'image_sha256': hashlib.sha256(data).hexdigest(),
            'image_size_bytes': len(data), 'image_name': path.name}
