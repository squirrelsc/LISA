import pathlib
import re

from lisa.executable import Tool
from lisa.operating_system import Linux
from lisa.util import LisaException, get_matched_str


class Git(Tool):
    CODE_FOLDER_PATTERN = re.compile(r"Cloning into '(.+)'")

    @property
    def command(self) -> str:
        return "git"

    @property
    def can_install(self) -> bool:
        return True

    def _install(self) -> bool:
        if isinstance(self.node.os, Linux):
            self.node.os.install_packages([self])
        else:
            raise LisaException(
                "Doesn't support to install git in Windows. "
                "Make sure git is installed and in PATH"
            )
        return self._check_exists()

    def clone(
        self, url: str, cwd: pathlib.PurePath, branch: str = "", dir_name: str = ""
    ) -> None:
        cmd = f"clone {url} {dir_name}"
        # git print to stderr for normal info, so set no_error_log to True.
        result = self.run(cmd, cwd=cwd, no_error_log=True)

        code_dir = get_matched_str(result.stderr, self.CODE_FOLDER_PATTERN)
        full_path = cwd / code_dir
        if branch:
            self.checkout(branch, cwd=full_path)

    def checkout(self, branch: str, cwd: pathlib.PurePath) -> None:
        self.run(f"checkout {branch}", cwd=cwd, no_info_log=True, no_error_log=True)
