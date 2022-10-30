# -*- coding: utf-8 -*-
import os
import datetime
import openpyxl
import re
import requests
from github import Github

def create_xl():

	#トークンでgithubにアクセス
	g = Github(os.environ.get('GITHUB_TOKEN'))

	#リポジトリにアクセス
	repo = g.get_repo('matanki-saito/vic3jpadvmod')
			
	#excelブックの準備
	book = openpyxl.Workbook()
	book.create_sheet(title='その他')

	#反復用の変数の準備/2行目と3列目
	ITR_FIRST_ROW = 2
	ITR_FIRST_COL = 3
	i=ITR_FIRST_COL
	j=ITR_FIRST_ROW
	#各issueに対して処理
	for _issue in repo.get_issues():
		issue = _issue
		headers = re.findall('##.*?\n|##.*?\r\n',issue.body)
		lines = re.split('##.*?\n|##.*?\r\n',issue.body)

		est_sheetnames = book.get_sheet_names()
		#issueに(タグ)がついていて、タグ名のシートがなければシートを作成
		if(issue.labels != []):
			if(issue.labels[0].name in book.sheetnames):
				pass
			else:
				book.create_sheet(title=issue.labels[0].name)
			#タグ名のシートを選択
			sheet = book[issue.labels[0].name]

		#タグが付いていない場合'その他'のシートを選択
		else:
			sheet = book['その他']

		#出来立てのシートには一行目に見出しを付ける
		if(sheet.max_row == 1):
			sheet.cell(row=1, column=1).value = 'Issue number'
			sheet.cell(row=1, column=2).value = 'Issue title'
			for h in headers:
				sheet.cell(row=1, column=sheet.max_column+1).value = h

		#issueの番号とタイトルを挿入する
		sheet.cell(row=sheet.max_row+1, column=1).value = issue.number
		sheet.cell(row=sheet.max_row, column=2).value = issue.title

		#issueの内容を挿入するのは選択したシートの最大行
		j = sheet.max_row

		#issueの内容を挿入する
		for l in lines:
			l2 = re.sub('\n|\r\n', '', l)
			if(l2 != ''):
				sheet.cell(row=j, column=i).value = l2
				i=i+1
		i=ITR_FIRST_COL
	
	#.xlsxファイルの保存先(例)：./issues/2022-10-30.xlsx
	xlname = './issues/'+str(datetime.date.today())+'.xlsx'
	book.save(xlname)

def main():
	create_xl()

if __name__ == "__main__":
	main()