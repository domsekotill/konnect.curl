#!/usr/bin/env python3
#
# Copyright 2023-2026  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
Script for generating stub packages from konnect.curl source code
"""

from __future__ import annotations

import sys
import tomllib
from copy import deepcopy
from pathlib import Path
from shutil import copyfile
from shutil import rmtree
from subprocess import run
from typing import TYPE_CHECKING

INSTALL_MSG = """
Please install the "stub-gen" dependency group in your development virtual environment.
i.e.:
  pip install --group stub-gen
"""

try:
	import tomli_w
except ModuleNotFoundError:
	sys.exit(INSTALL_MSG)

if TYPE_CHECKING:
	from collections.abc import Iterator
	from collections.abc import Mapping
	from collections.abc import Sequence

type ConfigType = Mapping[str, ConfigType] | Sequence[ConfigType] | int | float | bool | str
type Config = Mapping[str, ConfigType]


CWD = Path(".")

POETRY_CONFIG: Config = {
	"name": "types-konnect.curl",
	"version": "",
	"description": "static type stubs for konnect.curl",
	"packages": [
		{"include": "konnect-stubs"},
	],
	"authors": list[str](),
	"dependencies": dict[str, str](),
	"include": [
		"LICENCE.txt",
	],
	"license": "MPL-2.0",
}

STUB_PKG_CONFIG: Config = {
	"build-system": {
		"build-backend": "poetry.core.masonry.api",
		"requires": ["poetry_core>=1.0.0"],
	},
	"tool": {"poetry": POETRY_CONFIG},
}


def get_object(config: Config, *path: str | int) -> ConfigType:
	"""
	Return an object from the configuration object accessed by path keys/indexes
	"""
	obj: ConfigType = config
	for step in path:
		match obj:
			case list():
				if not isinstance(step, int):
					msg = f"need a list index, got {step!r}"
					raise TypeError(msg)
				obj = obj[step]
			case dict():
				if not isinstance(step, str):
					msg = f"need a mapping key string, got {step!r}"
					raise TypeError(msg)
				obj = obj[step]
			case _:
				msg = f"got a list index or mapping key where none expected"
				raise TypeError(msg)
	return obj


def get_config(config: Config, *path: str | int) -> dict[str, ConfigType]:
	"""
	Get a sub-config mapping from the configuration object accessed by path keys/indexes
	"""
	value = get_object(config, *path)
	if not isinstance(value, dict):
		raise TypeError(f"Not a mapping: {value!r}")
	return value


def get_array(config: Config, *path: str | int) -> list[ConfigType]:
	"""
	Return a list from the configuration object accessed by path keys/indexes
	"""
	sequence = get_object(config, *path)
	if not isinstance(sequence, list):
		raise TypeError(f"Not a sequence: {sequence!r}")
	return sequence


def get_str(config: Config, *path: str | int) -> str:
	"""
	Get a string from the configuration object accessed by path keys/indexes
	"""
	value = get_object(config, *path)
	if not isinstance(value, str):
		raise TypeError(f"Not a string: {value!r}")
	return value


def exec_module(module: str, *args: str | Path) -> None:
	"""
	Execute the named module from the environment with the given arguments
	"""
	run([sys.executable, "-m", module, *args], check=True)


def exec_bin(name: str, *args: str | Path) -> None:
	"""
	Execute a binary or script installed in the environment
	"""
	run([Path(sys.exec_prefix, "bin", name), *args], check=True)


class Project:
	"""
	Information about the root project
	"""

	def __init__(self, root: Path = CWD) -> None:
		self.root = root
		self._config: Config | None = None

	@property
	def config(self) -> Config:
		"""
		The project configuration (pyproject.toml) as a configuration mapping
		"""
		if not self._config:
			with open("pyproject.toml", "rb") as config:
				self._config = tomllib.load(config)
		return self._config

	def get_version(self) -> str:
		"""
		Return the project's version
		"""
		return get_str(self.config, "project", "version")

	def get_authors(self) -> Iterator[str]:
		"""
		Return an iterator over the project authors objects
		"""
		for author in get_array(self.config, "project", "authors"):
			if not isinstance(author, dict):
				raise TypeError(f"Not an author mapping: {author!r}")
			yield f"{author['name']} <{author['email']}>"

	def python_dependency(self) -> str:
		"""
		Return the python dependency specification for the project
		"""
		return get_str(self.config, "project", "requires-python")


class Package:
	"""
	Methods for preparing and building the stubs packages
	"""

	def __init__(self, project: Project) -> None:
		self.project = project

	def complete_config(self) -> Config:
		"""
		Return the package's configuration (pyproject.toml) as a mapping
		"""
		config = deepcopy(STUB_PKG_CONFIG)
		poetry = get_config(config, "tool", "poetry")
		assert isinstance(poetry["authors"], list)
		assert isinstance(poetry["dependencies"], dict)
		poetry["version"] = self.project.get_version()
		poetry["authors"].extend(self.project.get_authors())
		poetry["dependencies"].update(python=self.project.python_dependency())
		return config

	def build(self, build_dir: Path) -> None:
		"""
		Prepare and build the stubs package in build_dir
		"""
		if build_dir.exists():
			rmtree(build_dir)
		build_dir.mkdir(parents=True)
		with build_dir.joinpath("pyproject.toml").open("wb") as config:
			tomli_w.dump(self.complete_config(), config)
		self.copy_docs(build_dir)
		self.make_stubs(build_dir)
		self.build_package(build_dir)

	def copy_docs(self, build_dir: Path) -> None:
		"""
		Copy minimal documentation for the types stubs package
		"""
		copyfile(self.project.root / "LICENCE.txt", build_dir / "LICENCE.txt")

	def make_stubs(self, build_dir: Path) -> None:
		"""
		Generate type stub package
		"""
		exec_bin(
			"stubgen",
			"--verbose",
			"--output",
			build_dir / "konnect-stubs",
			self.project.root / "konnect/curl",
		)
		copyfile(
			self.project.root / "konnect/curl/__init__.py",
			build_dir / "konnect-stubs/curl/__init__.pyi",
		)
		copyfile(
			self.project.root / "konnect/curl/_enums.py",
			build_dir / "konnect-stubs/curl/_enums.pyi",
		)

	def build_package(self, build_dir: Path) -> None:
		"""
		Build distribution packages from generated sources
		"""
		exec_module(
			"build",
			"--outdir",
			self.project.root / "dist",
			build_dir,
		)


if __name__ == "__main__":
	project = Project()
	package = Package(project)
	package.build(Path("build/package"))
