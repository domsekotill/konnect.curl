# Copyright 2023  Dom Sekotill <dom.sekotill@kodo.org.uk>


class CurlError(Exception):
	"""
	An error exception for Curl transfers

	The value of 'code' is a Curl `CURLE_*` value, for instance `CURLE_COULDNT_CONNECT`.
	The value of 'msg' is an error message returned by `curl_easy_strerror` with 'code'
	passed as an argument.
	"""

	args: tuple[int, str]

	def __init__(self, code: int, msg: str):
		super().__init__(code, msg)

	def __str__(self) -> str:
		return f"Curl error: ({self.args[0]}) {self.args[1]}"

	@property
	def code(self) -> int:
		return self.args[0]

	@property
	def msg(self) -> str:
		return self.args[1]
