#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os

from boto3.session import Session


def main():
    region = "ap-northeast-1"
    bucket_name = "triela-credentials"
    access_key = os.environ.get("AWS_S3_ACCESS_KEY")
    secret_access_key = os.environ.get("AWS_S3_SECRET_ACCESS_KEY")

    # フォルダ用意
    os.makedirs("steamcmd", exist_ok=True)
    os.makedirs("steamcmd/config", exist_ok=True)

    # セッション確立
    session = Session(aws_access_key_id=access_key,
                      aws_secret_access_key=secret_access_key,
                      region_name=region)

    s3 = session.resource('s3')
    s3.Bucket(bucket_name).download_file("steamcmd/config.vdf",
                                         "steamcmd/config/config.vdf")


if __name__ == "__main__":
    main()
