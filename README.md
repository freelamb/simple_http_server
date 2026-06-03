# simple_http_server

[English](README.md) | [简体中文](README.zh-CN.md)

## Features

- ✔ simple
- ✔ upload
- ✔ batch upload
- ✔ download
- ✔ support python2, python3
- ✔ Multi-threaded
## Usage
```bash
# get code
$ git clone https://github.com/freelamb/simple_http_server.git

# enter directory
$ cd simple_http_server

# run server
$ python simple_http_server.py 8000

# optionally limit upload requests to 1 GiB
$ python simple_http_server.py --max-upload-size 1024 8000

# expose to another host in a trusted network
$ python simple_http_server.py --bind 0.0.0.0 8000
```

Install from PyPI:

```bash
$ python -m pip install simple-http-server-upload
$ simple-http-server-upload 8000
```

Run with Docker:

```bash
# pull the published image
$ docker pull freelamb/simple_http_server:latest

# serve the current directory on http://127.0.0.1:8000
$ docker run --rm -d \
  --name simple_http_server \
  -p 8000:8000 \
  -v "$PWD":/opt/data \
  freelamb/simple_http_server:latest
```

Build the Docker image locally:

```bash
$ docker build -t freelamb/simple_http_server:local .
$ docker run --rm -d \
  --name simple_http_server \
  -p 8000:8000 \
  -v "$PWD":/opt/data \
  freelamb/simple_http_server:local
```

## Security

This server is intended for temporary file sharing in trusted environments. The default bind address is `127.0.0.1`; use `--bind 0.0.0.0` only when you explicitly want other hosts to connect.

Uploaded file names are sanitized, and upload results and directory listings escape user-controlled text. Upload size is unlimited by default; use `--max-upload-size MIB` to set a limit when you need one in trusted environments.

## Example

![](image/example.jpeg)

## Contributing

1. Check for open issues or open a fresh issue to start a discussion around a feature idea or a bug.
2. Fork [the repository](https://github.com/freelamb/simple_http_server)_ on GitHub to start making your changes to the **master** branch (or branch off of it).
3. Write a test which shows that the bug was fixed or that the feature works as expected.
4. Send a pull request and bug the maintainer until it gets merged and published. :) Make sure to add yourself to [AUTHORS_](AUTHORS.md).

## License

[MIT](https://tldrlegal.com/license/mit-license)
