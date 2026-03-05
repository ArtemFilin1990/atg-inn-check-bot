from __future__ import annotations

import sys

from app import main


def test_ensure_project_root_on_syspath_adds_project_root(monkeypatch):
    monkeypatch.setattr(sys, "path", ["/tmp/other"])

    main._ensure_project_root_on_syspath("/workspace/atg-inn-check-bot/app/main.py")

    assert sys.path[0] == "/workspace/atg-inn-check-bot"


def test_ensure_project_root_on_syspath_avoids_duplicates(monkeypatch):
    monkeypatch.setattr(sys, "path", ["/workspace/atg-inn-check-bot", "/tmp/other"])

    main._ensure_project_root_on_syspath("/workspace/atg-inn-check-bot/app/main.py")

    assert sys.path.count("/workspace/atg-inn-check-bot") == 1
