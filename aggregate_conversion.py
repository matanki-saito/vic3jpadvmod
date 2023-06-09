import json
import os
import time
import urllib.request


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


def fetch_conversion_from_paratranz(project_id,
                                    secret,
                                    start_id,
                                    base_url="https://paratranz.cn"):

    result = {}

    for page in range(1, 999):
        regenerate_request_url = "{}/api/projects/{}/scores?page={}".format(base_url, project_id, page)
        req = urllib.request.Request(regenerate_request_url, method="GET")

        req.add_header("Authorization", secret)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))

            if page == 1:
                print("first id: %s" % data['results'][0]['id'])

            for record in data['results']:
                if start_id is not None and record["id"] <= start_id:
                    return result

                # 更新を除外するためmatankiはカウントから除外する
                if record['uid'] == 713:
                    continue

                if not record["uid"] in result:
                    result[record["uid"]] = 0

                result[record["uid"]] += record["value"]

            print("load page: %s" % page)

            if page >= data['pageCount']:
                break

            time.sleep(1)

    return result


def main():
    base_amount = int(os.environ.get("BASE_AMOUNT"))
    start_id = int(os.environ.get("START_ID"))
    paratranz_secret = os.environ.get("PARATRANZ_SECRET")
    adjustments = json.loads(os.environ.get("ADJUSTMENTS"))
    paratranz_project_id = 5456

    conversions = fetch_conversion_from_paratranz(project_id=paratranz_project_id,
                                                  secret=paratranz_secret,
                                                  start_id=start_id)

    id_name_map = fetch_user_from_paratranz(project_id=paratranz_project_id,
                                            secret=paratranz_secret)

    for uid, score in conversions.items():
        if id_name_map.get(uid) in adjustments:
            conversions[uid] += adjustments[id_name_map.get(uid)]

    total_score = 0
    for uid, score in conversions.items():
        total_score += score

    for uid, score in conversions.items():
        print("%s : %s : %s円" % (id_name_map.get(uid), int(score), int(score/total_score * base_amount)))


if __name__ == "__main__":
    main()
