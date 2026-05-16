from tools import git_diff
import pytest

def test_git_diff():
    diff = git_diff(".", "HEAD~1")
    print(diff)