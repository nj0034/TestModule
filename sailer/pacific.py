import json

import requests


LUNA_PACIFIC_ENDPOINT = "https://luna.devhi.me/pacific"
NOTICE_ARTICLE_PREFIX = "/article/notice"


def store_notice_article(**kwargs):
    body = {
        "no": kwargs.get("no"),
        "subject": kwargs.get("subject"),
        "content": kwargs.get("content"),
        "hit": kwargs.get("hit"),
        "writer": kwargs.get("writer"),
        "url": kwargs.get("url"),
        "created_at": kwargs.get("created_at"),
        "modified_at": kwargs.get("modified_at"),
    }
    res = requests.post(LUNA_PACIFIC_ENDPOINT + NOTICE_ARTICLE_PREFIX, data=body)
    if res:
        res = json.loads(res.text)
        print("Response of store_notice_article : ", str(res))
    return res
