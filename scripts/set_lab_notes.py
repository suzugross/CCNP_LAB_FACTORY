#!/usr/bin/env python3
"""CML の Lab Notes を任意ファイルの内容に差し替える(config 無変更・出題中でも安全)。

用途: 英語出題(BL-071)で、build_topology が埋め込んだ日本語 task.md の Notes を
      task.en.md に差し替える(quiz スキル「英語出題」節の手順)。

使い方:
  .venv/bin/python3 scripts/set_lab_notes.py <問題ID> <notesファイル>
  例: .venv/bin/python3 scripts/set_lab_notes.py ENARSI-VRFLITE-DNBIT-01 \
        problems/ENARSI-VRFLITE-DNBIT-01/task.en.md

ラボは topologies/_generated/<問題ID>/lab.yaml の lab.title (CCNP-LAB-*) で特定する。
認証は group_vars/all/local.yml (cml_host/cml_username/cml_password) を読む。
"""
import sys
from pathlib import Path

import urllib3
import yaml

REPO = Path(__file__).resolve().parent.parent


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    problem, notes_file = sys.argv[1], sys.argv[2]

    lab_yaml = REPO / "topologies" / "_generated" / problem / "lab.yaml"
    if not lab_yaml.exists():
        sys.exit(f"lab.yaml が見つからない(未provision?): {lab_yaml}")
    title = yaml.safe_load(lab_yaml.read_text(encoding="utf-8"))["lab"]["title"]

    conf = yaml.safe_load((REPO / "group_vars/all/local.yml").read_text(encoding="utf-8"))

    urllib3.disable_warnings()
    from virl2_client import ClientLibrary  # 遅延import

    cl = ClientLibrary(
        f"https://{conf['cml_host']}",
        conf["cml_username"],
        conf["cml_password"],
        ssl_verify=conf.get("cml_verify_cert", False),
    )
    labs = [l for l in cl.all_labs() if l.title == title]
    if not labs:
        sys.exit(f"CML 上にラボが見つからない: {title}")
    labs[0].notes = Path(notes_file).read_text(encoding="utf-8")
    print(f"OK: {title} ({problem}) の Notes を {notes_file} に差し替えた")


if __name__ == "__main__":
    main()
