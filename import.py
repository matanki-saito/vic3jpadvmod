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
    paratranz_zip_file: Path = Path("tmp/p.zip")
    base_url: str = "https://paratranz.cn"


class Context2:
    context: Context = None
    current_stats = None
    japanese_stats = None
    english_stats = None
    file_str_paths: set = None
    converted_root_path: Path = Path("tmp/converted")

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

    print("[LOG] status code {}".format(response.status_code))

    # wait for regenerate
    print("[LOG] wait 20sec")
    time.sleep(20)

    print("[LOG] Try to download current paratranz zip file")
    url = "{}/api/projects/{}/artifacts/download".format(ctx.base_url, ctx.project_id)
    response = requests.get(url, headers=headers)
    print("[LOG] status code {}".format(response.status_code))

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

    print("[LOG] status code {}".format(response.status_code))


def get_tid_from_key(key: str, context: Context):
    # 完全一致検索をするにはkeyではなくてkey@。 At markが必要
    url = "{}/api/projects/{}/strings?manage=1&key@={}&advanced=1".format(context.base_url, context.project_id, key)
    headers = {'Authorization': context.secret}

    print("[LOG] Get text id from key, key={}".format(key))

    response = requests.get(url, headers=headers)
    print("[LOG] status code {}".format(response.status_code))

    content = response.json()

    if len(content["results"]) != 1:
        return None

    return content["results"][0]["id"]


def update_entry_by_tid(tid: int, payload: dict, context: Context):
    url = "{}/api/projects/{}/strings/{}".format(context.base_url, context.project_id, tid)
    headers = {'Authorization': context.secret}

    print("[LOG] Update text from text id, text id={}".format(tid))

    response = requests.put(url, data=payload, headers=headers)

    print("[LOG] status code {}".format(response.status_code))


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

    print("[LOG] status code {}".format(response.status_code))


def output(ctx: Context2):
    file_str_paths_cache = ctx.file_str_paths.copy()

    result: Context3 = Context3(ctx)
    actions: dict = {}

    for str_path, keys in ctx.english_stats.items():
        path = Path(str_path.replace("english\\", "japanese\\")).with_suffix(".json")
        json_path = ctx.converted_root_path.joinpath(path)
        new_file_flag = False

        # 新規ファイル
        if str(path) not in file_str_paths_cache:
            print("[LOG] New file : {}".format(json_path.name))
            new_file_flag = True
        else:
            file_str_paths_cache.remove(str(path))

        data = []
        for key, record in keys.items():
            entry = {
                "key": key,
                "original": record["value"]
            }

            if new_file_flag:
                entry["context"] = ctx.japanese_stats[key]["value"]
                entry["translation"] = ctx.japanese_stats[key]["value"]

            elif key in ctx.current_stats:
                if key in ctx.japanese_stats:
                    entry["context"] = ctx.japanese_stats[key]["value"]
                    if record["value"] != ctx.current_stats[key]["original"]:
                        if ctx.current_stats[key]["context"] != ctx.japanese_stats[key]["value"]:
                            if ctx.current_stats[key]["context"] != ctx.current_stats[key]["translation"]:
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
                                    "translation": ctx.japanese_stats[key]["value"]
                                }
                        else:
                            if ctx.current_stats[key]["context"] != ctx.current_stats[key]["translation"]:
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
                        if ctx.current_stats[key]["context"] != ctx.japanese_stats[key]["value"]:
                            if ctx.current_stats[key]["context"] != ctx.current_stats[key]["translation"]:
                                # No.5
                                print("[Log] No.5 | {}".format(key))

                                # 更新予定の日本語翻訳＝Paratranzの翻訳ならば翻訳が受け入れられたと判断して状態変更はしない
                                if ctx.japanese_stats[key]["value"] == ctx.current_stats[key]["translation"]:
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
                            if ctx.current_stats[key]["context"] != ctx.current_stats[key]["translation"]:
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
                    entry["context"] = ctx.japanese_stats[key]["value"]
                    actions[key] = {
                        "stage": 1,  # translated,
                        "translation": ctx.japanese_stats[key]["value"]
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
        with open(file_path, 'r', encoding='utf_8_sig') as fr:
            for entry in json.load(fr):
                result[entry["key"]] = {
                    "translation": entry["translation"].replace("\\n", "\n") if "translation" in entry else None,
                    "original": entry["original"].replace("\\n", "\n"),
                    "stage": entry["stage"],
                    "context": entry["context"].replace("\\n", "\n") if "context" in entry else
                    entry["original"].replace("\\n", "\n")
                }
                result2.add(str(file_path.relative_to(utf8_path)))

    return result, result2


def aggregation_stats_from_japanese_files(ctx: Context):
    result = {}

    for file_path in pathlib.Path(ctx.japanese_root_path).glob('**/*.yml'):
        with open(file_path, 'r', encoding='utf_8_sig') as f:
            for line in f:
                match = re.search(r'^\s+([^:#]+):\d*\s+\"(.*)\"[^\"]*$', line)
                if match:
                    key = match.group(1)
                    value = match.group(2)
                    result[key] = {
                        "value": value.replace("\\n", "\n")
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
                match = re.search(r'^\s+([^:#]+):\d*\s+\"(.*)\"[^\"]*$', line)
                if match:
                    key = match.group(1)
                    value = match.group(2)
                    result[str_path][key] = {
                        "value": value.replace("\\n", "\n")
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
    os.makedirs("tmp", exist_ok=True)
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
        print(e)
        exit(1)

    update_files(context3)

    update_entry(context3)


if __name__ == "__main__":
    main()
