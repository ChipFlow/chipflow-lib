# gen-overrides.py
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pyproject-parser",
#   "requirements-parser",
# ]
# ///
import os
import subprocess
import sys
import urllib
from pathlib import Path

from pyproject_parser import PyProject
from requirements.requirement import Requirement


rootdir = Path(os.environ["PDM_PROJECT_ROOT"])

def get_branch(repo_dir):
    """Get the current git branch"""
    return subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip()

def get_remote_branch(repo, branch):
    return subprocess.call(
        ['git', 'ls-remote', '--exit-code', '--heads', repo, f'refs/heads/{branch}'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0

def gen_overrides():
    if len(sys.argv) > 1:
        branch = sys.argv[1]
        if branch.startswith("refs/heads/"):
            branch = branch[11:]
    else:
        branch = get_branch(rootdir)
    prj = PyProject.load(rootdir / "pyproject.toml")
    reqs = prj.project['dependencies']
    git_reqs = [r for r in reqs if r.url and r.url.startswith('git+')]
    for r in git_reqs:
        parts = urllib.parse.urlparse(r.url, allow_fragments=True)
        # remove any branches that might already be there
        base = parts.path.rsplit(sep="@",maxsplit=1)[0]
        clone_url = urllib.parse.urlunparse(parts._replace(path=base, scheme="https"))
        if get_remote_branch(clone_url, branch):
            path = f"{parts.path}@{branch}"
        else:
            path = parts.path
        r.url = urllib.parse.urlunparse(parts._replace(path=path))
        print(str(r))

if __name__ == "__main__":
    gen_overrides()
