import os
import re
import urllib.request
import json
import time
import openpyxl
from github import Github


def fetch_issues_from_github(lqa_version,
                             repository_name,
                             token):
    # トークンでgithubにアクセス
    g = Github(token)

    # リポジトリにアクセス
    repo = g.get_repo(repository_name)

    # milestone
    milestone = None
    for m in repo.get_milestones():
        if m.title == lqa_version:
            milestone = m
            break

    if milestone is None:
        raise Exception("milestone=%sが見つかりません" % milestone)

    # 各issueに対して処理
    result = {}
    issues = repo.get_issues(state='closed', milestone=milestone)
    for issue in issues:

        # 新issue形式では概要があるのでそれを使う
        reason = ""
        lines = re.split(r'### (.*)\n\n', issue.body)
        for i in range(0, len(lines)):
            if lines[i] == "変更の理由（概要）" and i+1 < len(lines):
                reason = lines[i+1].replace("\n", "")
                break

        # 古issue形式では変更の理由があるのでそれを使う
        if reason == "":
            lines = re.split(r'## (.*)', issue.body)
            for i in range(0, len(lines)):
                if re.search(r'変更の理由', lines[i]) and i+1 < len(lines):
                    reason = lines[i+1].replace("\n\n", "")
                    break

        result[issue.number] = {
            "assigner": issue.assignee.name,
            "closed_by": issue.closed_by,
            "reason": reason
        }

    return result


comment_m = re.compile(r'ISSUES?-?(\d+)', re.IGNORECASE)


def fetch_note_from_paratranz(project_id,
                              secret,
                              last_id,
                              base_url="https://paratranz.cn"):

    result = {}

    for page in range(1, 999):
        regenerate_request_url = "{}/api/comments?project={}&page={}".format(base_url, project_id, page)
        req = urllib.request.Request(regenerate_request_url, method="GET")

        req.add_header("Authorization", secret)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))

            if page == 1:
                print("first id: %s" % data['results'][0]['id'])

            for record in data['results']:
                if last_id is not None and record["id"] <= last_id:
                    return result

                m = comment_m.match(record['content'])
                if m:
                    result[record["tid"]] = {
                        "issue_number": int(m.group(1))
                    }

            print("load page: %s" % page)

            if page >= data['pageCount']:
                break

            time.sleep(1)

    return result


def fetch_fileid_from_paratranz(project_id,
                                secret,
                                base_url="https://paratranz.cn"):

    request_url = "{}/api/projects/{}/files".format(base_url, project_id)
    req = urllib.request.Request(request_url, method="GET")

    req.add_header("Authorization", secret)
    with urllib.request.urlopen(req) as response:
        result = {}
        for record in json.loads(response.read().decode("utf-8")):
            result[record["id"]] = "{}".format(record["name"])

        return result


def fetch_user_from_paratranz(project_id,
                              secret,
                              base_url="https://paratranz.cn"):

    regenerate_request_url = "{}/api/projects/{}/members".format(base_url, project_id)
    req = urllib.request.Request(regenerate_request_url, method="GET")

    req.add_header("Authorization", secret)
    with urllib.request.urlopen(req) as response:
        result = {}
        for record in json.loads(response.read().decode("utf-8")):
            result[record["user"]["id"]] = "{}".format(record["user"]["username"])

        return result


def fetch_history_from_paratranz(project_id,
                                 secret,
                                 last_id,
                                 base_url="https://paratranz.cn"):

    result = {}

    for page in range(1, 999):
        regenerate_request_url = "{}/api/history?project={}&page={}".format(base_url, project_id, page)
        req = urllib.request.Request(regenerate_request_url, method="GET")

        req.add_header("Authorization", secret)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))

            if page == 1:
                print("first id: %s" % data['results'][0]['id'])

            for record in data['results']:
                if last_id is not None and record["id"] <= last_id:
                    return result

                related = record['related']
                result[related['key']] = {
                    "fileId": related['fileId'],
                    "from": related['context'],
                    "to": related['translation'],
                    "uid": related['uid'],
                    "tid": related['id'],
                    "timestamp": related['updatedAt']
                }

            print("load page: %s" % page)

            if page >= data['pageCount']:
                break

            time.sleep(1)

    return result


def main():

    # ex) "1.1"
    target_lqa_version = os.environ.get("TARGET_LQA_VERSION")
    paratranz_secret = os.environ.get("PARATRANZ_SECRET")
    paratranz_project_id = 5456
    github_token = os.environ.get('GITHUB_TOKEN')

    # github issuesを取得
    issues = fetch_issues_from_github(lqa_version=target_lqa_version,
                                      repository_name='matanki-saito/vic3jpadvmod',
                                      token=github_token)

    id_name_map = fetch_user_from_paratranz(project_id=paratranz_project_id,
                                            secret=paratranz_secret)

    # file情報を取得
    id_file_map = fetch_fileid_from_paratranz(project_id=paratranz_project_id,
                                              secret=paratranz_secret)

    # 編集履歴を取得
    history = fetch_history_from_paratranz(project_id=paratranz_project_id,
                                           last_id=41433821,
                                           secret=paratranz_secret)

    # Note取得
    note = fetch_note_from_paratranz(project_id=paratranz_project_id,
                                     last_id=None,
                                     secret=paratranz_secret)

    # excelにする
    book = openpyxl.Workbook()
    book.remove(book.worksheets[-1])
    sheet = book.create_sheet(title="items")

    sheet.append(["file", "key", "from", "to", "author", "updatedAt", "reason", "issue"])
    for (key, value) in history.items():
        if value["from"] != value["to"]:
            reason = ""
            issue_number = ""

            if value["tid"] in note:
                issue_number = note.get(value["tid"])["issue_number"]

                if issue_number == 0:
                    reason = "構文の補正"

                elif issue_number in issues:
                    reason = issues.get(issue_number)["reason"]

            sheet.append([id_file_map.get(value['fileId']).replace(".json", ""),
                         key,
                         value["from"],
                         value["to"],
                         id_name_map.get(value["uid"]),
                         value["timestamp"],
                         reason,
                         issue_number])

    xlname = './issues/%s.xlsx' % target_lqa_version
    if os.path.exists(xlname):
        os.remove(xlname)

    book.save(xlname)
    book.close()


if __name__ == "__main__":
    main()
