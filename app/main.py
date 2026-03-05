import sys


def _ensure_project_root_on_syspath(project_root: str) -> None:
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

