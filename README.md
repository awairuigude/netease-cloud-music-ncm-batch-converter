# NetEase Cloud Music NCM Batch Converter

一个用于批量转换网易云音乐 `.ncm` 文件的 Python 3 工具。它会直接还原 NCM 内嵌的音频数据，不进行二次转码；源 `.ncm` 文件不会被修改。

> 仅处理你拥有合法使用权的本地音频文件。

## 功能

- 递归处理目录中的 `.ncm` 文件，并在输出目录保留原有文件夹结构
- 依据 NCM 元数据生成 MP3、FLAC 等实际音频扩展名
- 可选复制同名 `.lrc` 歌词文件
- 自动跳过已有输出；可用 `--overwrite` 覆盖
- 正确处理歌名中包含句点、中文、日文、韩文等字符的文件名

## 环境

- Python 3.10 或更高版本
- [PyCryptodome](https://www.pycryptodome.org/)

安装依赖：

```shell
python -m pip install -r requirements.txt
```

## 使用

```shell
python ncm_convert.py "D:\\CloudMusic\\VipSongsDownload" ".\\converted" --copy-lyrics
```

参数说明：

```text
source          包含 .ncm 文件的源目录
output          转换后的音频输出目录
--copy-lyrics   复制同名 .lrc 歌词
--overwrite     覆盖已有音频输出
```

转换结果会写入输出目录，原始 `.ncm` 与歌词文件保持不变。

## 范围

本项目是一个独立的 Python 实现，适合轻量级离线批处理。它不会联网获取封面，也不会重写音频标签或嵌入封面；如需这些功能，可使用更完整的桌面/命令行工具。

## 不要上传个人媒体

仓库的 `.gitignore` 已排除 `.ncm`、音频和歌词文件。请勿将下载的音乐或转换结果提交到仓库。

## 许可证

[MIT](LICENSE)