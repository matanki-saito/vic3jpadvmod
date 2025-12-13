import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import requests

STEAMCMD_PATH = os.environ.get("STEAMCMD_PATH", r"C:\steamcmd\steamcmd.exe")
APPID = int(os.environ.get("APPID", 529340))

REPO_OWNER = os.environ.get("REPO_OWNER", "matanki-saito")
REPO_NAME = os.environ.get("REPO_NAME", "vic3jpadvmod")

STEAM_LOGIN_NAME = os.environ.get("STEAM_LOGIN_NAME", "gnagaoka")

STEAM_GAME_DIR = os.environ.get("STEAM_GAME_DIR", "D:\\program\\vic3")

SOURCE_DIR = "./extract"

MY_GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN")


def run_steamcmd_info(appid: int) -> str:
    """
    SteamCMD を実行して app_info_print の出力を取得する
    """

    # 一時ファイルに出力させる
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    temp_path = temp_file.name
    temp_file.close()

    cmd = [
        STEAMCMD_PATH,
        "+login", "anonymous",
        "+app_info_update", "1",
        "+app_info_print", str(appid),
        "+quit"
    ]
    print(cmd)

    # SteamCMD 実行 ＋ stdout/stderr をファイルに保存
    with open(temp_path, "w", encoding="utf-8", errors="ignore") as f:
        result = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)

    # exit code を判定
    if result.returncode != 0:
        # エラーの中身を読んで例外に含める
        with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
            log = f.read()
        os.remove(temp_path)
        raise RuntimeError(
            f"SteamCMD failed (exit {result.returncode}). Log:\n{log}"
        )

    # 読み込み
    with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
        data = f.read()

    # 一時ファイル削除
    os.remove(temp_path)
    return data


def run_steamcmd_update(appid: int, game_dir: str, login_name: str) -> str:
    """
    SteamCMD を実行してゲームをupdateする
    """

    # 一時ファイルに出力させる
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    temp_path = temp_file.name
    temp_file.close()

    cmd = [
        STEAMCMD_PATH,
        "-dev",
        "-textmode",
        "-ignoredxsupportcfg",
        "+force_install_dir", game_dir,
        "+login", login_name,
        "+app_update", str(appid),
        "+quit"
    ]

    print(cmd)

    # SteamCMD の標準出力をファイルに保存
    with open(temp_path, "w", encoding="utf-8", errors="ignore") as f:
        subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)

    # 読み込み
    with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
        data = f.read()

    # 一時ファイル削除
    os.remove(temp_path)
    return data


def parse_buildids(text: str):
    """
    SteamCMD app_info_print の出力から buildid を抽出
    """

    depot_pattern = re.compile(
        r'"(?P<depot_id>\d+)"\s*\{[^}]*?"buildid"\s*"(?P<buildid>\d+)"',
        re.DOTALL
    )

    branch_block_pattern = re.compile(
        r'"branches"\s*\{(?P<block>.*?)\}',
        re.DOTALL
    )

    single_branch_pattern = re.compile(
        r'"(?P<branch>[^"]+)"\s*\{[^}]*?"buildid"\s*"(?P<buildid>\d+)"',
        re.DOTALL
    )

    result = {
        "depots": {},
        "branches": {}
    }

    # depot buildID の抽出
    for m in depot_pattern.finditer(text):
        d = m.group("depot_id")
        b = int(m.group("buildid"))
        result["depots"][d] = b

    # branch buildID の抽出
    m = branch_block_pattern.search(text)
    if m:
        block = m.group("block")
        for b in single_branch_pattern.finditer(block):
            branch = b.group("branch")
            buildid = int(b.group("buildid"))
            result["branches"][branch] = buildid

    return result


def get_latest_branch_public_number(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    r = requests.get(url)
    r.raise_for_status()

    body = r.json().get("body", "")

    m = re.search(r"Branch\s+public:\s*(\d+)", body)
    if not m:
        return -1

    return int(m.group(1))


def copy_items_from_base(base_dir, item_names, dest):
    """
    base_dir   : 元のフォルダ（この中からコピーしたいものを探す）
    item_names : base_dir 内のコピーしたい名前のリスト（ファイル名 or フォルダ名）
    dest       : コピー先ディレクトリ
    """
    base_dir = Path(base_dir)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)

    for name in item_names:
        src = base_dir / name

        if not src.exists():
            print(f"Skip (not found): {src}")
            continue

        target = dest / name

        # ---------- フォルダのコピー ----------
        if src.is_dir():
            if target.exists():
                shutil.rmtree(target)  # 上書きのため削除
            print(f"Copying directory: {src} → {target}")
            shutil.copytree(src, target)

        # ---------- ファイルのコピー ----------
        else:
            print(f"Copying file: {src} → {target}")
            shutil.copy2(src, target)


def empty_directory(dir_path):
    """
    指定フォルダ内のファイル・フォルダを全部削除し、空にする
    """
    d = Path(dir_path)

    if not d.exists() or not d.is_dir():
        print(f"Not a directory: {d}")
        return

    for item in d.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def run_git_command(cmd, cwd=None, ignore_error=False):
    """Git コマンドを実行するラッパー"""
    print(f"Running: {cmd}")

    try:
        subprocess.run(cmd, shell=True, check=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        if ignore_error:
            print(f"Non-critical error ignored: {e}")
        else:
            print(e.returncode, e.cmd, e.output)
            raise


def git_commit_and_push(repo_dir, commit_message, token):
    # 1) Git config
    # run_git_command('git remote add origin https://github.com/matanki-saito/eu5jpplus', cwd=repo_dir, ignore_error=True)

    run_git_command('git config --global user.email "matanki.saito@gmail.com"')
    run_git_command(f'git config --global user.name "{REPO_OWNER}"')

    # ★★ 追加：改行コード変換を無効化 ★★
    # run_git_command('git config --global core.autocrlf false')

    # 2) GitHub 認証設定
    run_git_command(
        f'git config --global url."https://{token}:x-oauth-basic@github.com/".'
        'insteadOf "https://github.com/"'
    )

    # 3) add
    run_git_command(f"git add {SOURCE_DIR}", cwd=repo_dir)

    # 4) commit（変更がなければ無視）
    run_git_command(
        f'git commit -m "{commit_message}"',
        cwd=repo_dir,
        ignore_error=True
    )

    # 5) push
    run_git_command("git push origin HEAD:main", cwd=repo_dir)


def read_branch_values(base_dir):
    # 読み込むファイル名
    caesar_file = os.path.join(base_dir, "caligula_branch.txt")
    clausewitz_file = os.path.join(base_dir, "clausewitz_branch.txt")

    # ファイル読み込み
    def read_file(path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()

    caesar_value = read_file(caesar_file)
    clausewitz_value = read_file(clausewitz_file)

    # 指定の形式で出力テキスト作成
    output_text = f"{caesar_value}+{clausewitz_value}"

    return output_text


def create_github_release(repo_owner, repo_name, token, tag_name, release_name, body=""):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    payload = {
        "tag_name": tag_name,
        "name": release_name,
        "body": body,
        "draft": False,
        "prerelease": False
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 201:
        print("✅ Release created successfully!")
        print("URL:", response.json().get("html_url"))
    else:
        print("❌ Failed to create release:")
        print(response.status_code, response.text)


def main():
    print(f"SteamCMD を使用して AppID {APPID} の buildID を取得します…")

    output = run_steamcmd_info(APPID)
    parsed = parse_buildids(output)

    print("\n=== Depot buildIDs ===")
    for d, b in parsed["depots"].items():
        print(f"  Depot {d}: {b}")

    public_id = -1
    print("\n=== Branch buildIDs ===")
    for name, b in parsed["branches"].items():
        print(f"  Branch {name}: {b}")
        if name == "public":
            public_id = b

    current_public_id = get_latest_branch_public_number(REPO_OWNER, REPO_NAME)
    if public_id == current_public_id:
        print("更新が不要です")
        return

    print("ゲーム更新を行います")
    os.makedirs(STEAM_GAME_DIR, exist_ok=True)
    # install_result = run_steamcmd_update(APPID, STEAM_GAME_DIR, STEAM_LOGIN_NAME)
    # print(install_result)

    print("フォルダクリア")
    empty_directory(SOURCE_DIR)

    print("対象を更新")
    extract_path = Path(SOURCE_DIR)
    base_path = Path(STEAM_GAME_DIR)

    japanese_root_path = extract_path.joinpath("japanese_root_path")
    shutil.copytree(base_path.joinpath(Path("game", "localization", "japanese")),
                    japanese_root_path.joinpath(Path("japanese")))
    shutil.copytree(base_path.joinpath(Path("jomini", "localization")), japanese_root_path.joinpath(Path("jomini")),
                    copy_function=jp_filter)
    shutil.copytree(base_path.joinpath(Path("clausewitz", "localization")),
                    japanese_root_path.joinpath(Path("clausewitz")), copy_function=jp_filter)

    english_root_path = extract_path.joinpath("english_root_path")
    shutil.copytree(base_path.joinpath(Path("game", "localization", "english")),
                    english_root_path.joinpath(Path("english")))
    shutil.copytree(base_path.joinpath(Path("jomini", "localization")), english_root_path.joinpath(Path("jomini")),
                    copy_function=en_filter)
    shutil.copytree(base_path.joinpath(Path("clausewitz", "localization")),
                    english_root_path.joinpath(Path("clausewitz")), copy_function=en_filter)

    shutil.copy2(base_path.joinpath(Path("caligula_branch.txt")), extract_path)
    shutil.copy2(base_path.joinpath(Path("clausewitz_branch.txt")), extract_path)

    print("タグ名を作成")
    tag_name = read_branch_values(SOURCE_DIR)
    print(tag_name)

    print("Git push")
    git_commit_and_push(
        repo_dir=".",
        commit_message="Extract files from game [ci skip]",
        token=MY_GITHUB_TOKEN
    )

    print("create release")
    create_github_release(REPO_OWNER, REPO_NAME, MY_GITHUB_TOKEN, tag_name, tag_name,
                          f"Branch public: {public_id}")


def jp_filter(src, dst):
    if re.search(r"l_japanese.yml$", src):
        shutil.copy2(src, dst)


def en_filter(src, dst):
    if re.search(r"l_english.yml$", src):
        shutil.copy2(src, dst)


if __name__ == "__main__":
    main()
