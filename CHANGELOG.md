<a name="0.3.5"></a>
## [0.3.5] (2026-06-03)
### Features

* add `--max-upload-size` to configure the upload request limit in MiB

### Bug Fixes

* return HTTP 413 for upload requests that exceed the configured limit

<a name="0.3.4"></a>
## [0.3.4] (2026-06-03)
### Bug Fixes

* preserve uploads that omit an optional part Content-Type header
* avoid truncating uploads whose content contains boundary-like text
* remove partial files when uploads end unexpectedly

<a name="0.3.3"></a>
## [0.3.3] (2026-06-03)
### Security

* sanitize uploaded filenames
* escape upload and directory listing output
* reject malformed upload headers and uploads larger than 100 MiB

### Features

* default to localhost binding
* serve requests with a threaded HTTP server
* add unit tests for helper behavior

<a name="0.2.1"></a>
## [0.2.1] (2021-10-17)
### Features

* fix windows signal SIGHUP error

<a name="0.2.0"></a>
## [0.2.0] (2021-05-04)
### Features

* support python3.x

<a name="0.1.2"></a>
## [0.1.2] (2020-07-24)
### Features

* fix Chinese garbled

<a name="0.1.0"></a>
## [0.1.0] (2018-04-10)

### Features

* finish copy code

<a name="0.0.1"></a>
## [0.0.1] (2018-04-10)

### Features

* init project
* confirm requirement
