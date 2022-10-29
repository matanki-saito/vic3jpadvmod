#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import pathlib
import shutil
import textwrap
import time
import urllib.request
import zipfile
import json
from os.path import join

import regex

_ = join


def download_trans_zip_from_paratranz(project_id,
                                      secret,
                                      out_file_path,
                                      base_url="https://paratranz.cn"):
    """
    paratranzからzipをダウンロードする。ダウンロード前にre-generateする
    :param project_id:
    :param secret:
    :param base_url:
    :param out_file_path:
    :return:
    """

    regenerate_request_url = "{}/api/projects/{}/artifacts".format(base_url, project_id)
    req = urllib.request.Request(regenerate_request_url, method="POST")
    req.add_header("Authorization", secret)
    with urllib.request.urlopen(req) as response:
        print(response.read().decode("utf-8"))

    # wait for regenerate
    time.sleep(90)

    download_request_url = "{}/api/projects/{}/artifacts/download".format(base_url, project_id)
    req = urllib.request.Request(download_request_url)
    req.add_header("Authorization", secret)

    with open(out_file_path, "wb") as my_file:
        my_file.write(urllib.request.urlopen(req).read())

    return out_file_path


def assembly_mod(resource_dir_path,
                 resource_paratranz_main_zip_file_path,
                 out_dir_path):
    """
    Appモッドを作成
    :param mod_file_name: Modファイル名
    :param resource_paratranz_main_zip_file_path: ParatranzからダウンロードできるMain Mod zipファイルのパス
    :param resource_dir_path: リソースディレクトリパス
    :param out_dir_path: 出力フォルダ
    :return:
    """

    ext_paratranz_main_dir_path = _(".", "tmp", "paratranz_ext_main")

    # 初期化（github-actionsでは必要ない）
    if os.path.exists(ext_paratranz_main_dir_path):
        shutil.rmtree(ext_paratranz_main_dir_path)
    if os.path.exists(out_dir_path):
        shutil.rmtree(out_dir_path)

    # zip展開する
    with zipfile.ZipFile(resource_paratranz_main_zip_file_path) as existing_zip:
        existing_zip.extractall(ext_paratranz_main_dir_path)

    # jsonをymlにする
    shutil.copytree(src=_(ext_paratranz_main_dir_path, "utf8"),
                    dst=_(out_dir_path, "localization"))
    convert_json_to_yml(_(out_dir_path, "localization"))

    # .metadata/metadata.jsonを入れる
    os.makedirs(_(out_dir_path, ".metadata"), exist_ok=True)
    generate_metadata_json_file(_(out_dir_path, ".metadata"), os.environ.get("RUN_NUMBER"), "1.0.*")

    return out_dir_path


def convert_json_to_yml(target_path):
    for file_path in pathlib.Path(target_path).glob('**/*.json'):
        with open(_(file_path.parent, file_path.stem + ".yml"), 'wt', encoding='utf-8', errors='ignore', newline='') as fw:
            fw.write("l_japanese:")
            with open(file_path, 'r', encoding='utf-8') as fr:
                for entry in json.load(fr):
                    fw.write(" %s:%s \"%s\"\n" % (entry["key"], entry["stage"], entry["translation"]))
        os.remove(file_path)


def generate_metadata_json_file(target_path, mod_version, game_version):
    text = textwrap.dedent("""\
        {
          "name" : "Japanese Language Advanced Mod",
          "id" : "",
          "version" : "0.%s.0",
          "supported_game_version" : "%s",
          "short_description" : "",
          "tags" : [],
          "relationships" : [],
          "game_custom_data" : {
            "multiplayer_synchronized" : true
          }
        }
    """ % (mod_version, game_version))

    with open(_(target_path, 'metadata.json'), 'wt') as fw:
        fw.write(text)


def update_source(mod_folder_path):
    shutil.rmtree("source/", ignore_errors=True)
    shutil.copytree(mod_folder_path, _("source", "JapaneseLanguageAdvancedMod"))


def main():
    # 一時フォルダ用意
    os.makedirs(_(".", "tmp"), exist_ok=True)
    os.makedirs(_(".", "out"), exist_ok=True)
    out_dir_path = _(".", "out")
    zip_path = _(".", "tmp", "paratranz_main.zip")

    # 翻訳の最新版をダウンロードする project_id=5456はVic3JPADMODのプロジェクトID
    if not os.path.exists(zip_path):
        p_file_main_path = download_trans_zip_from_paratranz(
            project_id=5456,
            secret=os.environ.get("PARATRANZ_SECRET"),
            out_file_path=zip_path)
        print("p_file_main_path:{}".format(p_file_main_path))
    else:
        p_file_main_path = zip_path

    # Modを構築する（フォルダのまま）
    mod_folder_path = assembly_mod(
        resource_paratranz_main_zip_file_path=p_file_main_path,
        resource_dir_path=_(".", "resource"),
        out_dir_path=out_dir_path)
    print("mod_dir_path:{}".format(out_dir_path))

    # utf8ファイルを移動する（この後git pushする）
    update_source(mod_folder_path=mod_folder_path)


if __name__ == "__main__":
    main()
