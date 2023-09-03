#!/usr/bin/env python3
#
# Copyright 2023  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
Script for generating stub packages from konnect.curl source code
"""

import sys
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from shutil import copyfile
from shutil import rmtree
from subprocess import run
from typing import Self
from typing import TypeAlias

import toml

CWD = Path(".")

POETRY_CONFIG = {
	"name": "types-konnect.curl",
	"version": "",
	"description": "static type stubs for konnect.curl",
	"packages": [
		{"include": "konnect-stubs"},
	],
	"authors": [],
	"dependencies": {},
}

STUB_PKG_CONFIG = {
	"build-system": {
		"build-backend": "poetry.core.masonry.api",
		"requires": ["poetry_core>=1.0.0"],
	},
	"tool": {"poetry": POETRY_CONFIG},
}


Config: TypeAlias = dict[str, object]


def get_object(config: Config, *path: str|int) -> object:
	"""
	Return an object from the configuration object accessed by path keys/indexes
	"""
	obj: object = config
	for step in path:
		obj = obj[step]  # type: ignore
	return obj


def get_config(config: Config, *path: str|int) -> Config:
	"""
	Get a sub-config mapping from the configuration object accessed by path keys/indexes
	"""
	value = get_object(config, *path)
	if not isinstance(value, dict):
		raise TypeError(f"Not a mapping: {value!r}")
	return value


def get_array(config: Config, *path: str|int) -> list[object]:
	"""
	Return a list from the configuration object accessed by path keys/indexes
	"""
	sequence = get_object(config, *path)
	if not isinstance(sequence, list):
		raise TypeError(f"Not a sequence: {sequence!r}")
	return sequence


def get_str(config: Config, *path: str|int) -> str:
	"""
	Get a string from the configuration object accessed by path keys/indexes
	"""
	value = get_object(config, *path)
	if not isinstance(value, str):
		raise TypeError(f"Not a string: {value!r}")
	return value


class Environment:
	"""
	A simple virtual environment (venv) interface
	"""

	def __init__(self, path: Path):
		self.path = path
		self.bin = path / "bin"
		self.python = self.bin / "python"

	def __enter__(self) -> Self:
		if self.python.is_file():
			return self
		run([sys.executable, "-mvenv", self.path], check=True)
		return self

	def __exit__(self, *exc_info: object) -> None:
		pass

	def install(self, package: str) -> None:
		"""
		Install the named package in the environment
		"""
		self.exec_module("pip", "install", package)

	def exec_module(self, module: str, *args: str|Path) -> None:
		"""
		Execute the named module from the environment with the given arguments
		"""
		run([self.python, "-m", module, *args], check=True)


class Project:
	"""
	Information about the root project
	"""

	def __init__(self, root: Path = CWD):
		self.root = root
		self._config: Config|None = None

	@property
	def config(self) -> Config:
		"""
		The project configuration (pyproject.toml) as a configuration mapping
		"""
		if not self._config:
			with open("pyproject.toml") as config:
				self._config = toml.load(config)
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

	def __init__(self, project: Project):
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
		with build_dir.joinpath("pyproject.toml").open("w") as config:
			toml.dump(self.complete_config(), config)
		with Environment(build_dir / "stub.venv") as env:
			self.make_stubs(build_dir, env)
			self.build_package(build_dir, env)

	@staticmethod
	def make_stubs(build_dir: Path, env: Environment) -> None:
		"""
		Generate type stub package
		"""
		env.install("mypy")
		env.exec_module(
			"mypy.stubgen",
			"--verbose",
			"--output", build_dir / "konnect-stubs",
			"konnect/curl",
		)
		copyfile("konnect/curl/_enums.py", build_dir / "konnect-stubs/curl/_enums.pyi")

	def build_package(self, build_dir: Path, env: Environment) -> None:
		"""
		Build distribution packages from generated sources
		"""
		env.install("build")
		env.exec_module(
			"build",
			"--outdir", self.project.root / "dist",
			build_dir,
		)


if __name__ == "__main__":
	project = Project()
	package = Package(project)
	package.build(Path("build/package"))
