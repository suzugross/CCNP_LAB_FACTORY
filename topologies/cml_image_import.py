#!/usr/bin/env python3
"""refplat 形式の ISO から、選んだイメージだけを CML に登録する(ISO を CML にマウントしない・root 不要)。

  ls     ISO                 : ISO に入っているイメージ定義(virl-base-images/<id>/)とノード定義を一覧
  import ISO ID [ID ...]     : 指定したイメージを取り出して CML にアップロード → イメージ定義を登録
                               (既に登録済みの ID は飛ばす。ノード定義は CML 側の既存のものを使う)

対象は CML の refplat ISO と、cml-docker-containers の container ISO(services/browser/splunk)。
手元の置き場= ~/cml-images/(README.md に何があるかを書いてある)。BL-250/251。

★イメージ定義 yaml の sha256 は tar.gz のハッシュではなく Docker イメージ ID(manifest の Config)。
★同じファイルを共有する定義は、登録時にファイルが定義のフォルダへ移るので 1 件ずつアップロードし直す。

認証は group_vars/all/local.yml の cml_*(cml_snapshot.py と同じ)。
"""
import argparse
import sys
import tempfile
from pathlib import Path

import pycdlib
import yaml

ROOT = Path(__file__).resolve().parent.parent


def open_iso(path):
    iso = pycdlib.PyCdlib()
    iso.open(str(path))
    return iso


def listdir(iso, path):
    for c in iso.list_children(rr_path=path):
        if c.is_dot() or c.is_dotdot():
            continue
        name = c.rock_ridge.name()
        yield (name.decode() if isinstance(name, bytes) else name), c


def read_text(iso, path):
    with tempfile.NamedTemporaryFile() as fh:
        iso.get_file_from_iso_fp(fh, rr_path=path)
        fh.seek(0)
        return fh.read().decode("utf-8")


def images(iso):
    """{image_id: (dir, yaml dict)}"""
    out = {}
    for d, c in listdir(iso, "/virl-base-images"):
        if not c.is_dir():
            continue
        for f, _ in listdir(iso, f"/virl-base-images/{d}"):
            if f.endswith(".yaml"):
                y = yaml.safe_load(read_text(iso, f"/virl-base-images/{d}/{f}"))
                out[y["id"]] = (d, y)
    return out


def cmd_ls(a):
    iso = open_iso(a.iso)
    for iid, (d, y) in sorted(images(iso).items()):
        size = sum(c.get_data_length() for _, c in listdir(iso, f"/virl-base-images/{d}"))
        print(f"{iid:<36} node={y.get('node_definition_id'):<18} {size / 1e6:8.1f} MB  {y.get('label', '')}")
    nds = [n for n, _ in listdir(iso, "/node-definitions")]
    print(f"\nノード定義 {len(nds)} 件: {', '.join(sorted(nds))}")


def cmd_import(a):
    from virl2_client import ClientLibrary
    loc = yaml.safe_load((ROOT / "group_vars/all/local.yml").read_text(encoding="utf-8"))
    cl = ClientLibrary(f"https://{loc['cml_host']}", loc["cml_username"], loc["cml_password"], ssl_verify=False)
    have_img = {x["id"] for x in cl.definitions.image_definitions()}
    have_nd = {x["id"] for x in cl.definitions.node_definitions()}
    iso = open_iso(a.iso)
    imgs = images(iso)
    bad = [i for i in a.ids if i not in imgs]
    if bad:
        sys.exit(f"ISO に無い ID: {', '.join(bad)}(ls で確認)")
    for iid in a.ids:
        d, y = imgs[iid]
        if iid in have_img:
            print(f"skip(登録済み) {iid}")
            continue
        if y["node_definition_id"] not in have_nd:
            print(f"★skip {iid}: CML にノード定義 {y['node_definition_id']} が無い(ISO の node-definitions/ から先に入れる)")
            continue
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / y["disk_image"]
            iso.get_file_from_iso(str(dst), rr_path=f"/virl-base-images/{d}/{y['disk_image']}")
            print(f"upload {y['disk_image']} ({dst.stat().st_size / 1e6:.1f} MB)", flush=True)
            cl.definitions.upload_image_file(str(dst))
        cl.definitions.upload_image_definition(y)
        print(f"  define OK {iid}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("ls"); p.add_argument("iso"); p.set_defaults(f=cmd_ls)
    p = sp.add_parser("import"); p.add_argument("iso"); p.add_argument("ids", nargs="+"); p.set_defaults(f=cmd_import)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
