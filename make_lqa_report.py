import json
import os
import re
import time
import urllib.request
from datetime import datetime

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
            if lines[i] == "変更の理由（概要）" and i + 1 < len(lines):
                reason = lines[i + 1].replace("\n", "")
                break

        # 古issue形式では変更の理由があるのでそれを使う
        if reason == "":
            lines = re.split(r'## (.*)', issue.body)
            for i in range(0, len(lines)):
                if re.search(r'変更の理由', lines[i]) and i + 1 < len(lines):
                    reason = lines[i + 1].replace("\n\n", "")
                    break

        try:
            result[issue.number] = {
                "assigner": issue.assignee.name,
                "closed_by": issue.closed_by,
                "reason": reason
            }
        except Exception as e:
            print("issue number: %s, labels: %s" % (issue.number, issue.labels))

    return result


# スペルミスを許容, 数値だけも許容
comment_m = re.compile(r'^(ISSUES?|isuue)?-?(\d+)$', re.IGNORECASE)


def fetch_note_from_paratranz(project_id,
                              secret,
                              last_id,
                              base_url="https://paratranz.cn"):
    result = {}

    for page in range(0, 999):
        regenerate_request_url = "{}/api/comments?project={}&page={}".format(base_url, project_id, page)
        req = urllib.request.Request(regenerate_request_url, method="GET")

        req.add_header("Authorization", secret)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))

            if page == 1:
                print("note first id: %s" % data['results'][0]['id'])

            for record in data['results']:
                if last_id is not None and record["id"] <= last_id:
                    return result

                m = comment_m.match(record['content'])
                if m:
                    t = record["tid"]
                    if t not in result:
                        result[t] = {
                            "issue_numbers": []
                        }
                    else:
                        print("already exist: %s" % t)

                    result[t]["issue_numbers"].append({
                        "number": int(m.group(2)),
                        # 2023-03-18T07:46:09.121Z
                        "date": datetime.strptime(record["createdAt"], "%Y-%m-%dT%H:%M:%S.%f%z")
                    })

            print("load page: %s" % page)

            if page >= data['pageCount']:
                break

            time.sleep(0.1)

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
    overwrite_keys = set()

    for page in range(0, 999):
        regenerate_request_url = "{}/api/history?type=edit&project={}&page={}".format(base_url, project_id, page)
        req = urllib.request.Request(regenerate_request_url, method="GET")

        req.add_header("Authorization", secret)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))

            if page == 1:
                print("history record first id: %s" % data['results'][0]['id'])

            for record in data['results']:
                if last_id is not None and record["id"] <= last_id:
                    print("overwrite_keys; %s" % overwrite_keys)
                    return result

                related = record['related']

                if len(related) > 0:
                    if related['key'] in result:
                        overwrite_keys.add(related['key'])

                    result[related['key']] = {
                        "fileId": related['fileId'],
                        "from": related['context'],
                        "to": related['translation'],
                        "uid": related['uid'],
                        "tid": related['id'],
                        "timestamp": datetime.strptime(record['createdAt'], "%Y-%m-%dT%H:%M:%S.%f%z")
                    }
                else:
                    print("empty : %s" % record)

            print("load page: %s" % page)

            if page >= data['pageCount']:
                break

            time.sleep(0.1)

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
        from_str = (value["from"] if value["from"] is not None else "").replace("\n", "\\n")
        to_str = value["to"] if value["to"] is not None else ""
        if from_str != to_str:
            reason = ""
            issue_number = ""

            if value["tid"] in note:
                issue_numbers = note.get(value["tid"])["issue_numbers"]

                issue_number = -2

                for item in issue_numbers:
                    tds = (item["date"] - value["timestamp"]).total_seconds()
                    if 0 < tds < (3600 * 24 * 180):
                        issue_number = item["number"]
                    if -3600 < tds <= 0:
                        print("minus: %s" % key)
                        issue_number = item["number"]

                if issue_number == 0:
                    reason = "構文の補正"
                elif issue_number == -2:
                    reason = "ISSUEなし"
                    print("unknown key :  %s" % key)
                elif issue_number in issues:
                    reason = issues.get(issue_number)["reason"]
            else:
                print("noteなし: %s, key: %s" % (value["tid"], key))

            sheet.append([id_file_map.get(value['fileId']).replace(".json", ""),
                          key,
                          from_str,
                          to_str,
                          id_name_map.get(value["uid"]),
                          value["timestamp"].strftime('%Y-%m-%dT%H:%M:%S.%f%z'),
                          reason,
                          issue_number])

    xlname = './issues/%s.xlsx' % target_lqa_version
    if os.path.exists(xlname):
        os.remove(xlname)

    book.save(xlname)
    book.close()


if __name__ == "__main__":
    main()
