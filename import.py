import os
import re
import shutil
import sys
import json
import pathlib
import urllib
from os.path import join
import requests
from pathlib import Path

_ = join


def output(japanese_dict, converted_root_path, english_root_path, path):

	original_path = os.path.join(english_root_path, path)
	files = os.listdir(original_path)

	for file in files:
		original_file = str(os.path.join(original_path, file))
		converted_path = os.path.join(converted_root_path, path)
		converted_file = str(os.path.join(converted_path, file))

		# In case of directory

		if os.path.isdir(original_file):
			if not os.path.exists(converted_file):
				pathlib.Path(converted_file).mkdir()
			output(japanese_dict, converted_root_path, english_root_path, os.path.join(path, file))

		# In case of file

		else:
			json_list = []
			print('Processing ' + original_file + '...')
			with open(original_file, 'r', encoding='utf_8_sig') as f:
				for line in f:
					res = re.search(r'^\s+([^:]+):\d+\s+\"(.*)\"[^\"]*$', line)
					if res:
						key = res.group(1)
						value = res.group(2)
						if key in japanese_dict:
							english = value
							japanese = japanese_dict.get(key)
							entry = {
								'key': key,
								'original': english,
								'translation': japanese,
								'context': japanese
							}
							json_list.append(json.dumps(entry, indent='\t'))
						else:
							print('Error: Unknown Key ' + key)
							sys.exit()
			with open(converted_file.replace('.yml', '.json'), 'w', encoding='utf-8') as f:
				f.write('[\n')
				f.write(',\n'.join(json_list))
				f.write('\n]\n')


def jp_filter(src, dst):
	if re.search(r"l_japanese.yml$", src):
		shutil.copy2(src, dst)


def en_filter(src, dst):
	if re.search(r"l_english.yml$", src):
		shutil.copy2(src, dst)


def update_file(base_path, source_path, project_id, secret, base_url="https://paratranz.cn"):
	# https://paratranz.cn/api/projects/5456/files
	# POST
	# arg1 : file : binary
	# arg2 : path: /clausewitz/text_utils
	# Content-Type: multipart/form-data;
	# Content-Length: 751

	file_name = os.path.basename(source_path)
	file_data_binary = open(source_path, 'rb').read()
	files = {
		'file': (file_name, file_data_binary,  'application/json; charset=utf-8'),
		'path': str(Path(source_path).relative_to(Path(base_path)).parent)
	}

	url = "{}/api/projects/{}/files".format(base_url, project_id)
	headers = {'Authorization': secret}
	response = requests.post(url, files=files, headers=headers)

	print(response)


def main():
	root_path = "./tmp/import"
	shutil.rmtree(root_path, ignore_errors=True)
	os.makedirs(root_path, exist_ok=True)

	converted_root_path = _(root_path, "converted")
	os.makedirs(converted_root_path, exist_ok=True)

	base_path = "C:\Program Files (x86)\Steam\steamapps\common\Victoria 3"

	japanese_root_path = _(root_path, "japanese_root_path")
	os.makedirs(japanese_root_path, exist_ok=True)
	shutil.copytree(_(base_path, "game", "localization", "japanese"), _(japanese_root_path, "japanese"))
	shutil.copytree(_(base_path, "jomini", "localization"), _(japanese_root_path, "jomini"), copy_function=jp_filter)
	shutil.copytree(_(base_path, "clausewitz", "localization"), _(japanese_root_path, "clausewitz"), copy_function=jp_filter)

	english_root_path = _(root_path, "english_root_path")
	os.makedirs(english_root_path, exist_ok=True)
	shutil.copytree(_(base_path, "game", "localization", "english"), _(english_root_path, "english"))
	shutil.copytree(_(base_path, "jomini", "localization"), _(english_root_path, "jomini"), copy_function=en_filter)
	shutil.copytree(_(base_path, "clausewitz", "localization"), _(english_root_path, "clausewitz"), copy_function=en_filter)

	# Create Japanese Dictionary

	japanese_dict = {}

	for root, dirs, files in os.walk(japanese_root_path):
		for filename in files:
			path = os.path.join(root, filename)
			print('Processing ' + path + '...')
			with open(path, 'r', encoding='utf_8_sig') as f:
				for line in f:
					res = re.search(r'^\s+([^:]+):\d+\s+\"(.*)\"[^\"]*$', line)
					if res:
						key = res.group(1)
						value = res.group(2)
						japanese_dict[key] = value

	# Output Json Files
	output(japanese_dict, english_root_path=english_root_path, converted_root_path=converted_root_path, path='')

	# update_file(
	# 	base_path=converted_root_path,
	# 	source_path=_(converted_root_path, "clausewitz", "cw_tools_l_english.json"),
	# 	secret=os.environ.get("PARATRANZ_SECRET"),
	# 	project_id=5456)


if __name__ == "__main__":
	# execute only if run as a script
	main()
