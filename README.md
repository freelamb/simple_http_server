# simple_http_server

## Features

- ✔ simple
- ✔ upload
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

# expose to another host in a trusted network
$ python simple_http_server.py --bind 0.0.0.0 8000

# run as docker container
# 1.build the image('.' below refer to the root path of this project)
docker build -t freelamb/simple_http_server .
# 2.run the container using the image built just now in docker 
docker run 
  --name simple_http_server \ 
  -p 8000:8000 \ 
  -v /opt/data:/opt/data \ 
  -d freelamb/simple_http_server:latest
```

## Security

This server is intended for temporary file sharing in trusted environments. The default bind address is `127.0.0.1`; use `--bind 0.0.0.0` only when you explicitly want other hosts to connect.

Uploaded file names are sanitized, upload results and directory listings escape user-controlled text, and uploads larger than 100 MiB are rejected.

## Example

![](image/example.jpeg)

## Todo
- [ ] add docker images
- [ ] add to pypi
## Contributing

1. Check for open issues or open a fresh issue to start a discussion around a feature idea or a bug.
2. Fork [the repository](https://github.com/freelamb/simple_http_server)_ on GitHub to start making your changes to the **master** branch (or branch off of it).
3. Write a test which shows that the bug was fixed or that the feature works as expected.
4. Send a pull request and bug the maintainer until it gets merged and published. :) Make sure to add yourself to [AUTHORS_](AUTHORS.md).

## Changelog

[Changelog](CHANGELOG.md)

## reference

<https://github.com/tualatrix/tools/blob/master/SimpleHTTPServerWithUpload.py>

## License

[MIT](https://tldrlegal.com/license/mit-license)
