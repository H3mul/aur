#!/usr/bin/env python3
"""Run in a package dir: fail if upstream pyproject.toml deps are missing from PKGBUILD depends.

Sources are fetched with `makepkg -od` (as $MAKEPKG_PREFIX, e.g. "sudo -u builder").
Overrides, as comments in the PKGBUILD:
  # deps-check: skip                    skip the whole package
  # deps-check: ignore aiohttp foo-bar  PyPI names to exempt (optional deps, renamed Arch pkgs)
"""
import glob, os, re, shlex, subprocess, sys, tomllib

norm = lambda n: re.sub(r"[-_.]+", "-", n).lower()
pkgbuild = open("PKGBUILD").read()
if re.search(r"^#\s*deps-check:\s*skip\b", pkgbuild, re.M):
    sys.exit("::notice::deps-check: skip set, not checking")
ignore = {norm(n) for m in re.findall(r"^#\s*deps-check:\s*ignore\s+(.*)$", pkgbuild, re.M) for n in m.split()}

subprocess.run([*shlex.split(os.environ.get("MAKEPKG_PREFIX", "")), "makepkg", "-od", "--noconfirm"], check=True)
# git sources land at src/<name>, tarballs at src/<name>-<ver>/
files = glob.glob("src/*/pyproject.toml")
if not files:
    sys.exit("::warning::no src/*/pyproject.toml, cannot check (add '# deps-check: skip' to silence)")
deps = tomllib.load(open(files[0], "rb")).get("project", {}).get("dependencies", [])

have = set(re.findall(r"'([^']+)'|\"([^\"]+)\"", re.search(r"^depends=\((.*?)\)", pkgbuild, re.M | re.S).group(1)))
have = {a or b for a, b in have}
want = {norm(re.match(r"[A-Za-z0-9_.-]+", d).group()) for d in deps} - ignore
missing = sorted(n for n in want if f"python-{n}" not in have)
if missing:
    sys.exit(f"::error::{os.getcwd()}: depends missing python-{{{','.join(missing)}}} "
             "(add them, or '# deps-check: ignore <pypi-name>')")
print("depends OK")
