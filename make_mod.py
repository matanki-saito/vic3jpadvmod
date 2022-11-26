#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import pathlib
import shutil
import textwrap
import urllib.request
import zipfile
import json
from os.path import join
import re
import time

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


def assembly_mod(resource_paratranz_main_zip_file_path,
                 out_dir_path):
    """
    Appモッドを作成
    :param resource_paratranz_main_zip_file_path: ParatranzからダウンロードできるMain Mod zipファイルのパス
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

    # jominiのフォルダをreplaceに移動する
    os.makedirs(_(out_dir_path, "localization", "replace"), exist_ok=True)
    shutil.move(src=_(out_dir_path, "localization", "jomini"),
                dst=_(out_dir_path, "localization", "replace"))

    # .metadata/metadata.jsonを入れる
    os.makedirs(_(out_dir_path, ".metadata"), exist_ok=True)
    generate_metadata_json_file(_(out_dir_path, ".metadata"), os.environ.get("RUN_NUMBER"), "1.0.*")

    return out_dir_path


def convert_json_to_yml(target_path):
    for file_path in pathlib.Path(target_path).glob('**/*.json'):
        with open(_(file_path.parent, file_path.stem.replace("l_english", "l_japanese") + ".yml"),
                  'wt', encoding='utf_8_sig', errors='ignore', newline='') as fw:
            fw.write("l_japanese:\n")
            with open(file_path, 'r', encoding='utf-8') as fr:
                for entry in json.load(fr):
                    translation = entry["translation"]

                    # ISSUE-493のWA
                    if not entry["key"] in ["RANK_TOOLTIP_NEXT", "RANK_TOOLTIP_PREV", "COUNTRY_RANK_TOOLTIP"]:
                        # [Nbsp]の表記ゆれを直して実態にする。
                        translation = re.sub(r'\[[Nn][Bb][Ss][Pp]]', " ", translation)
                        translation = issue_242(translation)
                        translation = issue_241(translation)
                    else:
                        print("skip:%s" % entry["key"])

                    # textのversionはParatranzに読み込めないので0とする
                    # "はエスケープしなくて良い
                    fw.write(" %s:%s \"%s\"\n" % (entry["key"], 0, translation))
        os.remove(file_path)


# マスク
mask_k = {":": "▲",
        "|": "△",
        "-": "■",
        "+": "□",
        ";": "▼",
        "\"": "◆",
        "'": "▣",
        ",": "▓",
        "[": "★",
        "]": "☆",
        "(": "✦",
        ")": "✧",
        ".": "✡"}

mask_r = dict(zip(mask_k.values(), mask_k.keys()))

mask_k_p = "|".join(map(re.escape, mask_k.keys()))
mask_r_p = "|".join(map(re.escape, mask_r.keys()))


def k(x):
    return re.sub(mask_k_p, lambda y: mask_k.get(y.group()), x)


def r(x):
    return re.sub(mask_r_p, lambda y: mask_r.get(y.group()), x)


# 記号の問題
def issue_241(text):
    """
    ・幅調整
     全角：は半角:と前後にスペース１つを入れる
     ビュレット•は前後にスペース１つを入れる
     ()は半角に合わせてスペース１つを入れる

    ・レンジの統一
     数字-数字は数字 ～ 数字にする
     日付-日付は日付 ～ 日付にする
     [最大]-[最小]は[最大] ～ [最小]にする

    ・符号統一
     値の前にある-はそのままにする

    ・約物統一
     文章の最後の.は。にする
     文章中の,は、にする

    :param text:
    :return:
    """

    # \wが壊れている？ので使用禁止 [a-zA-Z0-9_]

    # mask
    text = re.sub(r'(#[a-zA-Z0-9_]+(;[a-zA-Z0-9_]+)*(:([\da-zA-Z\[\].$_\'()#\-+=|%]+,?)+)?)\s',
                  lambda x: k(x.group(1)) + "♉", text)
    text = re.sub(r'\[[^]]+]', lambda x: k(x.group()), text)  # 実行処理
    text = re.sub(r'[a-zA-Z0-9_]+\([^)]+\)', lambda x: k(x.group()), text)  # 関数
    text = re.sub(r'\$[a-zA-Z0-9_|+=\-%]+\$', lambda x: k(x.group()), text)  # 変数
    text = re.sub(r'\'[^\']*\'', lambda x: k(x.group()), text)  # 文字列

    # 値の符号は保持する
    text = re.sub(r'-\$(AMOUNT|VAL|MAINTENANCE)', lambda x: k(x.group()), text)
    text = re.sub(r'-[0-9]+', lambda x: k(x.group()), text)
    text = re.sub(r'-★WarParticipant✡GetNumDead', lambda x: k(x.group()), text)
    text = re.sub(r'#N♉-', lambda x: k(x.group()), text)
    text = re.sub(r'#[N|P]♉*#(bold|BOLD)♉*-', lambda x: k(x.group()), text)
    text = re.sub(r'@money!-', lambda x: k(x.group()), text)

    # 幅調整
    text = re.sub(r'：',  r' : ', text)
    text = re.sub(r'[  ]*:[  ]*',  r' : ', text)
    text = re.sub(r'[  ]*•[  ]*', r' • ', text)
    text = re.sub(r'[  ]*[（(][  ]*',  r' (', text)
    text = re.sub(r'[  ]*[）)][  ]*',  r') ', text)

    # レンジ
    text = re.sub(r'([０-９\d]+)[\s ]*[-～][\s ]*([０-９\d]+)', r'\1 ～ \2', text)
    text = re.sub(r'(\$MIN([^$]*)\$)([^$]+)(\$MAX\2)',
                  lambda x: x.group(1) + x.group(3).replace("-", " ～ ") + x.group(4),
                  text)
    text = re.sub(r'(\$DAYS_MIN([^$]*)\$)([^$]+)(\$DAYS_MAX\2)',
                  lambda x: x.group(1) + x.group(3).replace("-", " ～ ") + x.group(4),
                  text)
    text = re.sub(r'(\$DURATION_MIN([^$]*)\$)([^$]+)(\$DURATION_MAX\2)',
                  lambda x: x.group(1) + x.group(3).replace("-", " ～ ") + x.group(4),
                  text)
    text = re.sub(r'\$★DATE_MIN✡GetStringShort△V☆\$\s*-\s*\$★DATE_MAX✡GetStringShort△V☆\$',
                  r'$★DATE_MIN✡GetStringShort△V☆$ ～ $★DATE_MAX✡GetStringShort△V☆$',
                  text)

    #text = re.sub(r'(?<!\||\d|v|=|%|K)-(?!(\$VAL|\$AMOUNT))', r' xxxx ', text)

    text = text.replace("-", "―")
    text = re.sub(r'[‐−–]', '‑', text)
    text = re.sub(r'－ｰ', 'ー', text)
    text = re.sub(r'—', '―', text)

    text = re.sub(mask_r_p, lambda x: r(x.group()), text)
    text = text.replace("♉", " ")

    return text


# 半角スペースの問題
def issue_242(text):
    """
    ・以下のアイコンには後ろにスペースを１つ入れる。指定アイコンは下記の通り。
     - simple_box : 空のチェックボックス
     - red_cross : 赤Xのチェックボックス
     - green_checkmark_box : 緑✔のチェックボックス
     - warning : 赤い！
     - information : 青い！
     - $FLAG_ICON$ : 国旗

    ・以下のアイコンの後ろのスペースは削除
     - スペースを入れなかった@xxx!のアイコン
     - [Goods.GetTextIcon] : 交易品
     - $GOODS_ICON$ : 交易品

    ・開始タグの後ろにスペースを1つ入れる。

    ・アイコンの前にあるスペースは削除

    ・/の前後にあるスペースは削除

    ・引用文 'xxxx' 中にあるスペースはnbspにする（word-wrapで改行させないため）
    ・関数中にあるスペースは削除する

    ・日本語 記号　ー＞ スペース削除
    ・記号 日本語 ー＞ スペース削除

    ・上記以外のすべてのスペースはNBSPにする（改行対策）

    ・伸ばし棒の調整
        ‐：ハイフン。約物として使うが1つも存在しない（改行のないハイフンに揃える）
        ‑：改行のないハイフン。1箇所だけ使われている（残す）
        −：マイナス。演算用として使うが1つも存在しない（改行のないハイフンに揃える）
        –：アンダッシュ。1つも存在しない（改行のないハイフンに揃える）
        -：ハイフンマイナス。マイナス記号とハイフンの両方として大量に使われている。（改行のないハイフンに揃える）
        ―：水平バー。間を開けるために3箇所使われている（残す）
        ー：全角長音符。日本語の一般的な伸ばし棒。大量にある。（残す）
        ｰ：半角長音符。上の半角バージョン。ムハンマド・アリムデｨｰンのような形で3つの人名で使われている。（全角長音符に揃える）
        —：全角ダッシュ。和文の組版で使われる。1箇所だけ使われている。（水平バーに揃える）
        －：全角ハイフン。一箇所（ディトサーン）だけ使われている。（全角長音符に揃える）
                ↓
        ‑：改行のないハイフン
        ー：全角長音符
        ―：水平バー

    :param text:
    :return:
    """

    text = re.sub(r'[ 　 ]*(@[^!]+!)[ 　 ]*',  r'\1', text)

    text = re.sub(r'@(warning|information|simple_box|red_cross|green_checkmark_box)![  ]*', r'@\1! ', text)
    text = re.sub(r'(\$FLAG_ICON\$|\$GOODS_ICON\$)[  ]*', r'\1 ', text)
    text = re.sub(r'(\[Goods\.GetTextIcon]|\$GOODS_ICON\$)[  ]*', r'\1', text)

    text = re.sub(r'(#[$a-zA-Z0-9_]+(;[a-zA-Z0-9_]+)*(:([\da-zA-Z\[\].$_\'()#\-+=|%]+,?)*)?)[  ]?', r'\1▲', text)

    # text = re.sub(r'#![  ]', r'#!', text)

    text = re.sub(r'[  ]*/[  ]*', r'/', text)

    text = re.sub(r'(\'[^\']*\')', lambda x: re.sub(r' ', ' ', x.group()), text)  # 引用文
    text = re.sub(r'\[[^]]+]', lambda x: re.sub(r' ', '', x.group()), text)  # 実行処理

    text = re.sub(r'([\[.\-+)($\]#])[  ]+([ぁ-んァ-ヶｱ-ﾝﾞﾟ一-龠])', r'\1\2', text)
    text = re.sub(r'([ぁ-んァ-ヶｱ-ﾝﾞﾟ一-龠])[  ]+([\[.\-+)($\]#])', r'\1\2', text)

    text = re.sub(r'\][  ]+\[', r'][', text)
    text = re.sub(r'#![  ]+\'', '#!\'', text)

    text = text.replace(' ', ' ')

    text = text.replace('▲', ' ')

    return text


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
        out_dir_path=out_dir_path)
    print("mod_dir_path:{}".format(out_dir_path))

    # utf8ファイルを移動する（この後git pushする）
    update_source(mod_folder_path=mod_folder_path)


if __name__ == "__main__":
    main()
    shutil.copytree(src="./out/localization",
                    dst="C:\\Program Files (x86)\\Steam\\steamapps\\workshop\\content\\529340\\2881605374\\localization",
                    dirs_exist_ok=True)

