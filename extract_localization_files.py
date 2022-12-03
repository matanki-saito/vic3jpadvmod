import os
import re
import shutil
from os.path import join
from pathlib import Path

_ = join


def jp_filter(src, dst):
	if re.search(r"l_japanese.yml$", src):
		shutil.copy2(src, dst)


def en_filter(src, dst):
	if re.search(r"l_english.yml$", src):
		shutil.copy2(src, dst)


def main():
	extract_path = Path("./extract")
	shutil.rmtree(extract_path, ignore_errors=True)
	os.makedirs(extract_path, exist_ok=True)

	base_path = Path("./tmp/game")
	#base_path = Path("C:\Program Files (x86)\Steam\steamapps\common\Victoria 3")

	japanese_root_path = extract_path.joinpath("japanese_root_path")
	shutil.copytree(base_path.joinpath(Path("game", "localization", "japanese")), japanese_root_path.joinpath(Path("japanese")))
	shutil.copytree(base_path.joinpath(Path("jomini", "localization")), japanese_root_path.joinpath(Path("jomini")), copy_function=jp_filter)
	shutil.copytree(base_path.joinpath(Path("clausewitz", "localization")), japanese_root_path.joinpath(Path("clausewitz")), copy_function=jp_filter)

	english_root_path = extract_path.joinpath("english_root_path")
	shutil.copytree(base_path.joinpath(Path("game", "localization", "english")), english_root_path.joinpath(Path("english")))
	shutil.copytree(base_path.joinpath(Path("jomini", "localization")), english_root_path.joinpath(Path("jomini")), copy_function=en_filter)
	shutil.copytree(base_path.joinpath(Path("clausewitz", "localization")), english_root_path.joinpath(Path("clausewitz")), copy_function=en_filter)


if __name__ == "__main__":
	main()
