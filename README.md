[![gitlab-ico]][gitlab-link]
<!-- [![github-ico]][github-link] -->
[![licence-mpl20]](/LICENCE.txt)
[![pre-commit-ico]][pre-commit-link]
<!-- [![pipeline-status]][pipeline-report] -->
<!-- [![coverage status]][coverage report] -->


Konnect
=======

Konnect is a project to make the power of the [libcurl multi][] feature available through 
a Pythonic interface.  It consists of this core package (konnect.curl) through which any 
protocol provided by libcurl can be accessed and some additional packages (e.g. 
konnect.http) which provide enhanced interfaces for specific protocols.


Basic Usage
-----------

Users must first create a class that implements the `konnect.curl.abc.RequestProtocol` 
interface; the methods of this protocol are essentially hooks that are called at certain 
points in a transfer.  The transfer commences when an instance of the request class is 
passed to `konnect.curl.Multi.process()` and the returned awaitable is awaited:

- `configure_handle` is called prior to connection with a single 
	`konnect.curl.abc.ConfigHandle` object as an argument.  This object can be used to 
	configure the request in a manner familiar to users of libcurl, by calling the 
	`konnect.curl.abc.ConfigHandle.setopt()` method of the object.  In particular users should 
	configure libcurl callbacks to handle various additional events specific to the desired 
	protocol.

- `has_update` & `get_update` are called continuously throughout the transfer. The latter, 
	if it returns anything, interrupts the transfer and returns the value from 
	`konnect.curl.Multi.process()`.  The user would normally then continue the transfer by 
	calling `konnect.curl.Multi.process()` again with the same multi and request objects.  It 
	is up to the user to recognise when the return is an interim response or a final response, 
	normally by checking the type of the response. If the implementation has nothing to return 
	during the transfer `has_update` can simply return `False` every time it is called.

- `completed` is called after the transfer is finished, with 
	a `konnect.curl.abc.GetInfoHandle` object that may be used to examine information about 
	the transfer in a way familiar to libcurl users, with it's 
	`konnect.curl.abc.GetInfoHandle.getinfo()` and 
	`konnect.curl.abc.GetInfoHandle.getinfo_raw()` methods.


Instances of `konnect.curl.Multi` are shareable within a thread and although it is possible 
to use multiple instances it is recommended for performance and resource usage reasons to 
use only one.  


[libcurl multi]:
	https://curl.se/libcurl/c/libcurl-multi.html
	"libcurl mutli interface overview"

[gitlab-ico]:
  https://img.shields.io/badge/GitLab-code.kodo.org.uk-blue.svg?logo=gitlab
  "GitLab"

[gitlab-link]:
  https://code.kodo.org.uk/konnect/konnect.curl
  "Konnect at code.kodo.org.uk"

[github-ico]:
  https://img.shields.io/badge/GitHub-domsekotill/konnect.curl-blue.svg?logo=github
  "GitHub"

[github-link]:
	https://github.com/domsekotill/kilter.protocol
	"Konnect at github.com"

[pre-commit-ico]:
  https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
  "Pre-Commit: enabled"

[pre-commit-link]:
  https://github.com/pre-commit/pre-commit
  "Pre-Commit at GitHub.com"

[licence-mpl20]:
  https://img.shields.io/badge/Licence-MPL--2.0-blue.svg
  "Licence: Mozilla Public License 2.0"

[pipeline-status]:
  https://code.kodo.org.uk/konnect/konnect.curl/badges/main/pipeline.svg

[pipeline-report]:
  https://code.kodo.org.uk/konnect/konnect.curl/pipelines/latest
  "Pipelines"

[coverage status]:
  https://code.kodo.org.uk/konnect/konnect.curl/badges/main/coverage.svg

[coverage report]:
  https://code.kodo.org.uk/konnect/konnect.curl/-/jobs/artifacts/main/file/results/coverage.html.d/index.html?job=Unit+Tests
