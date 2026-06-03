# simple_http_server

[English](README.md) | [简体中文](README.zh-CN.md)

## 功能

- 简单易用
- 支持上传
- 支持批量上传
- 支持下载
- 支持 Python 2 和 Python 3
- 支持多线程

## 使用方法

```bash
# 获取代码
$ git clone https://github.com/freelamb/simple_http_server.git

# 进入目录
$ cd simple_http_server

# 启动服务
$ python simple_http_server.py 8000

# 可选：将上传请求限制为 1 GiB
$ python simple_http_server.py --max-upload-size 1024 8000

# 在可信网络中允许其他主机访问
$ python simple_http_server.py --bind 0.0.0.0 8000
```

从 PyPI 安装：

```bash
$ python -m pip install simple-http-server-upload
$ simple-http-server-upload 8000
```

使用 Docker 运行：

```bash
# 拉取已发布镜像
$ docker pull freelamb/simple_http_server:latest

# 将当前目录挂载到容器中，并通过 http://127.0.0.1:8000 访问
$ docker run --rm -d \
  --name simple_http_server \
  -p 8000:8000 \
  -v "$PWD":/opt/data \
  freelamb/simple_http_server:latest
```

本地构建 Docker 镜像：

```bash
$ docker build -t freelamb/simple_http_server:local .
$ docker run --rm -d \
  --name simple_http_server \
  -p 8000:8000 \
  -v "$PWD":/opt/data \
  freelamb/simple_http_server:local
```

## 安全说明

这个服务用于可信环境中的临时文件共享。默认绑定地址是 `127.0.0.1`；只有在明确希望其他主机连接时，才使用 `--bind 0.0.0.0`。

上传文件名会被清理，上传结果和目录列表会对用户可控文本做 HTML 转义。上传大小默认不设上限；如需限制上传大小，可以在可信环境中使用 `--max-upload-size MIB`。

## 示例

![](image/example.jpeg)

## 贡献

1. 检查已有 issue，或新建 issue 来讨论功能想法或问题。
2. 在 GitHub 上 fork [本仓库](https://github.com/freelamb/simple_http_server)，从 **master** 分支开始修改，或基于它创建新分支。
3. 编写测试，证明问题已经修复，或功能符合预期。
4. 提交 pull request，并持续跟进直到合并和发布。记得把自己添加到 [AUTHORS](AUTHORS.md)。

## 许可证

[MIT](https://tldrlegal.com/license/mit-license)
