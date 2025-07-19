import json
import os
import pathlib
import re
import shutil
import tempfile
import time
import zipfile
from os.path import join
from pathlib import Path

import requests

_ = join


class Context:
    secret: str = os.environ.get("PARATRANZ_SECRET")
    project_id: int = 5456
    extract_path: Path = Path("extract")
    japanese_root_path: Path = Path("extract/japanese_root_path")
    english_root_path: Path = Path("extract/english_root_path")
    paratranz_zip_file: Path = Path("tmp3/p.zip")
    base_url: str = "https://paratranz.cn"
    is_local: bool = "IS_LOCAL" in os.environ and os.environ.get(
        "IS_LOCAL") in ["True", "true", 1]


class Context2:
    context: Context = None
    current_stats = None
    japanese_stats = None
    english_stats = None
    file_str_paths: set = None
    converted_root_path: Path = Path("tmp3/converted")

    def __init__(self, context: Context,
                 current_stats: dict,
                 japanese_stats: dict,
                 english_stats: dict,
                 file_str_paths: set):
        self.context = context
        self.current_stats = current_stats
        self.japanese_stats = japanese_stats
        self.english_stats = english_stats
        self.file_str_paths = file_str_paths

        shutil.rmtree(self.converted_root_path, ignore_errors=True)
        os.makedirs(self.converted_root_path)


class Context3:
    actions: dict = {}
    deleted_files: list = []
    context: Context2 = None

    def __init__(self, context: Context2):
        self.context = context


def get_file_infos(context: Context):
    # https://paratranz.cn/api/projects/5456/files
    # GET

    url = "{}/api/projects/{}/files".format(context.base_url, context.project_id)
    headers = {'Authorization': context.secret}
    response = json.loads(requests.get(url, headers=headers).text)

    result = {}
    for record in response:
        if record["name"].startswith("/"):
            record["name"] = record["name"][1:]

        result[record["name"]] = record["id"]

    return result


def get_current_paratranz_zip_file(ctx: Context):
    if ctx.paratranz_zip_file.exists():
        print("[Skip] already exists current paratranz zip file")
        return

    print("[LOG] Regenerate zip file")

    url = "{}/api/projects/{}/artifacts".format(ctx.base_url, ctx.project_id)
    headers = {'Authorization': ctx.secret}
    response = requests.post(url, headers=headers)

    print("[LOG] status code {} {}".format(response.status_code, response.text.encode("utf-8")))

    # wait for regenerate
    print("[LOG] wait 20sec")
    time.sleep(20)

    print("[LOG] Try to download current paratranz zip file")
    url = "{}/api/projects/{}/artifacts/download".format(ctx.base_url, ctx.project_id)
    response = requests.get(url, headers=headers)
    print("[LOG] status code {} {}".format(response.status_code, response.text.encode("utf-8")))

    with open(ctx.paratranz_zip_file, "wb") as my_file:
        my_file.write(response.content)


def update_current_file(file_id: int, source_path: Path, context: Context):
    file_name = source_path.name
    file_data_binary = open(source_path, 'rb').read()
    files = {
        'file': (file_name, file_data_binary, 'application/json; charset=utf-8')
    }

    print("[LOG] Update file, id={}, path={}".format(file_id, str(source_path)))

    url = "{}/api/projects/{}/files/{}".format(context.base_url, context.project_id, file_id)
    headers = {'Authorization': context.secret}
    response = requests.post(url, files=files, headers=headers)

    print("[LOG] status code {} {}".format(response.status_code, response.text.encode("utf-8")))


def get_tid_from_key(key: str, context: Context):
    # 完全一致検索をするにはkeyではなくてkey@。 At markが必要
    url = "{}/api/projects/{}/strings?manage=1&key@={}&advanced=1".format(context.base_url, context.project_id, key)
    headers = {'Authorization': context.secret}

    print("[LOG] Get text id from key, key={}".format(key))

    response = requests.get(url, headers=headers)
    print("[LOG] status code {} {}".format(response.status_code, response.text.encode("utf-8")))

    content = response.json()

    if len(content["results"]) != 1:
        return None

    return content["results"][0]["id"]


def update_entry_by_tid(tid: int, payload: dict, context: Context):
    url = "{}/api/projects/{}/strings/{}".format(context.base_url, context.project_id, tid)
    headers = {'Authorization': context.secret}

    print("[LOG] Update text from text id, text id={}".format(tid))

    response = requests.put(url, data=payload, headers=headers)

    print("[LOG] status code {} {}".format(response.status_code, response.text.encode("utf-8")))


def add_new_file(base_path: Path, source_path: Path, context: Context):
    file_name = source_path.name
    file_data_binary = open(source_path, 'rb').read()
    data = {'path': str(Path("/").joinpath(source_path.relative_to(base_path).parent)).replace("\\", "/")}
    files = {
        'file': (file_name, file_data_binary, 'application/yaml; charset=utf-8')
    }

    print("[LOG] Add new file, file_name={}".format(file_name))

    url = "{}/api/projects/{}/files".format(context.base_url, context.project_id)
    headers = {'Authorization': context.secret}
    response = requests.post(url, files=files, data=data, headers=headers)

    print("[LOG] status code {} {}".format(response.status_code, response.text.encode("utf-8")))


def pick_tool(dic: dict):
    if len(dic) > 1:
        print("WARN: {}".format(dic))

    for k, v in dic.items():
        return v


def output(ctx: Context2):
    file_str_paths_cache = ctx.file_str_paths.copy()

    result: Context3 = Context3(ctx)
    actions: dict = {}

    for str_path, keys in ctx.english_stats.items():
        path = Path(str_path.replace("english\\", "japanese\\")).with_suffix(".json")
        json_path = ctx.converted_root_path.joinpath(path)

        # 新規ファイル
        if str(path) not in file_str_paths_cache:
            print("[LOG] New file : {}".format(json_path.name))
        else:
            file_str_paths_cache.remove(str(path))

        data = []
        for key, en in keys.items():
            entry = {
                "key": key,
                "original": en["value"]
            }

            if key in ctx.current_stats:
                # keyの移動なし
                if en["parent"] in ctx.current_stats[key]:
                    cur = ctx.current_stats[key][en["parent"]]
                else:
                    # key移動あり。過去のデータを参照する
                    print("[LOG] move key {}".format(key))
                    cur = pick_tool(ctx.current_stats[key])

                if key in ctx.japanese_stats:
                    jp = ctx.japanese_stats[key][en["parent"]]
                    entry["context"] = jp["value"]
                    if en["value"] != cur["original"]:
                        if cur["context"] != jp["value"]:
                            if cur["context"] != cur["translation"]:
                                # No.1
                                print("[Log] No.1 | {}".format(key))
                                actions[key] = {
                                    "stage": 2,  # disputed
                                }
                            else:
                                # No.2
                                print("[Log] No.2 | {}".format(key))
                                actions[key] = {
                                    "stage": 1,  # translated
                                    "translation": jp["value"]
                                }
                        else:
                            if cur["context"] != cur["translation"]:
                                # No.3
                                print("[Log] No.3 | {}".format(key))
                                actions[key] = {
                                    "stage": 2,  # disputed
                                }
                            else:
                                # No.4
                                print("[Log] No.4 | {}".format(key))
                                actions[key] = {
                                    "stage": 1,  # translated
                                }
                    else:
                        if cur["context"] != jp["value"]:
                            if cur["context"] != cur["translation"]:
                                # No.5
                                print("[Log] No.5 | {}".format(key))

                                # 更新予定の日本語翻訳＝Paratranzの翻訳ならば翻訳が受け入れられたと判断して状態変更はしない
                                if jp["value"] == cur["translation"]:
                                    pass
                                else:
                                    actions[key] = {
                                        "stage": 2,  # disputed
                                    }
                            else:
                                # No.6
                                print("[Log] No.6 | {}".format(key))
                                pass
                        else:
                            if cur["context"] != cur["translation"]:
                                # No.7
                                # print("[Log] No.7 | {}".format(efc))
                                pass
                            else:
                                # No.8
                                # print("[Log] No.8 | {}".format(key))
                                pass
                else:
                    print("[Log] Japanese has been removed | {}".format(key))

            else:
                if key in ctx.japanese_stats:
                    print("[Log] No.10 | {}".format(key))
                    entry["context"] = pick_tool(ctx.japanese_stats[key])["value"]
                    actions[key] = {
                        "stage": 1,  # translated,
                        "translation": pick_tool(ctx.japanese_stats[key])["value"]
                    }
                else:
                    print("[Log] No.11 | {}".format(key))

            data.append(entry)

        if len(data) > 0:
            if not json_path.parent.exists():
                os.makedirs(json_path.parent, exist_ok=True)
            with open(json_path, 'wt', encoding='utf_8_sig') as fw:
                fw.write(json.dumps(data, indent=2))

    result.deleted_files = file_str_paths_cache
    result.actions = actions

    return result


def jp_filter(src, dst):
    if re.search(r"l_japanese.yml$", src):
        shutil.copy2(src, dst)


def en_filter(src, dst):
    if re.search(r"l_english.yml$", src):
        shutil.copy2(src, dst)


def aggregation_stats_from_current_files(ctx: Context):
    result = {}
    result2 = set()

    tmpdir_path = Path(tempfile.TemporaryDirectory().name)
    with zipfile.ZipFile(ctx.paratranz_zip_file) as existing_zip:
        existing_zip.extractall(tmpdir_path)

    utf8_path = tmpdir_path.joinpath("utf8")

    for file_path in pathlib.Path(utf8_path).glob('**/*.json'):
        relative_path = file_path.relative_to(utf8_path)
        str_path = str(relative_path)
        with open(file_path, 'r', encoding='utf_8_sig') as fr:
            for entry in json.load(fr):
                key = entry["key"]

                if key in result:
                    print("DUP(CUR) KEY: {}".format(key))
                else:
                    result[key] = {}

                result[key][str_path.replace("_l_english.json", "")] = {
                    "translation": entry["translation"] if "translation" in entry else None,
                    "original": entry["original"],
                    "stage": entry["stage"],
                    "context": entry["context"] if "context" in entry else
                    entry["original"],
                }
                result2.add(str(file_path.relative_to(utf8_path)))

    return result, result2


def aggregation_stats_from_japanese_files(ctx: Context):
    result = {}

    for file_path in pathlib.Path(ctx.japanese_root_path).glob('**/*.yml'):
        relative_path = file_path.relative_to(ctx.japanese_root_path)
        str_path = str(relative_path)
        with open(file_path, 'r', encoding='utf_8_sig') as f:
            for line in f:
                match = re.search(r'^\s*([^:#]+):\d*\s+\"(.*)\"[^\"]*$', line)
                if match:
                    key = match.group(1)
                    value = match.group(2)

                    if key in result:
                        print("DUP(JP) KEY: {}".format(key))
                    else:
                        result[key] = {}

                    result[key][str_path.replace("_l_japanese.yml", "")] = {
                        "value": value,
                    }

    return result


def aggregation_stats_from_english_files(ctx: Context):
    result = {}

    for file_path in pathlib.Path(ctx.english_root_path).glob('**/*.yml'):
        relative_path = file_path.relative_to(ctx.english_root_path)
        str_path = str(relative_path)
        result[str_path] = {}
        with open(file_path, 'r', encoding='utf_8_sig') as f:
            for line in f:
                match = re.search(r'^\s*([^:#]+):\d*\s+\"(.*)\"[^\"]*$', line)
                if match:
                    key = match.group(1)
                    value = match.group(2)
                    result[str_path][key] = {
                        "value": value,
                        "parent": str_path.replace("english\\", "japanese\\").replace("_l_english.yml", "")
                    }

    return result


def update_files(ctx: Context3):
    name2id = get_file_infos(context=ctx.context.context)
    for f in ctx.context.converted_root_path.glob("**/*.json"):
        pure = str(f.relative_to(ctx.context.converted_root_path)).replace("\\", "/")

        if pure not in name2id:
            add_new_file(
                base_path=ctx.context.converted_root_path,
                source_path=f,
                context=ctx.context.context)
        else:
            update_current_file(
                file_id=name2id[pure],
                source_path=f,
                context=ctx.context.context)

    # TODO: delete files


def update_entry(ctx: Context3):
    for key, value in ctx.actions.items():
        tid = get_tid_from_key(key=key, context=ctx.context.context)
        if tid is None:
            print("[ERROR] Failed to get tid from key, key={}".format(key))
        else:
            update_entry_by_tid(tid=tid, payload=value, context=ctx.context.context)


def main():
    os.makedirs("tmp3", exist_ok=True)
    context: Context = Context()

    get_current_paratranz_zip_file(ctx=context)
    current_stats, file_str_paths = aggregation_stats_from_current_files(ctx=context)
    japanese_stats = aggregation_stats_from_japanese_files(ctx=context)
    english_stats = aggregation_stats_from_english_files(ctx=context)

    context2: Context2 = Context2(context=context,
                                  japanese_stats=japanese_stats,
                                  current_stats=current_stats,
                                  english_stats=english_stats,
                                  file_str_paths=file_str_paths)
    try:
        context3: Context3 = output(context2)
    except Exception as e:
        import traceback
        print(e)
        print(traceback.format_exc())
        exit(1)

    update_files(context3)

    update_entry(context3)

    if not context.is_local:
        shutil.rmtree("tmp3")


if __name__ == "__main__":
    main()
