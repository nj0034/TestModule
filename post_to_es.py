import json
import os
from elasticsearch import Elasticsearch
from sailer.sailer import Sailer
import uuid
import re

DEFAULT_FILEPATH = "C:/Users/nj/PycharmProjects/TestModule/"
es = Elasticsearch('https://search-toast-test-4gvyyphmm2klzciadaeqkkzkza.ap-northeast-2.es.amazonaws.com')


def post_parsing_json():
    index = "parsing-json"
    es.delete_by_query(index=index, body={"query": {"match_all": {}}})

    for root, dirs, files in os.walk('json'):
        for fname in files:
            full_fname = os.path.join(root, fname)
            json_data = open(full_fname, encoding='UTF8').read()
            XPATH_JSON = json.loads(json_data)
            site_name = XPATH_JSON['meta']['site_name']
            print(site_name)
            es.create(index=index, doc_type="_doc", id=uuid.uuid4(),
                      body={"site_name": site_name, "json": XPATH_JSON})


post_parsing_json()


def post_policy_html():
    for root, dirs, files in os.walk('new_policy_html'):
        for fname in files:
            full_fname = os.path.join(root, fname)
            html = open(full_fname, encoding='UTF8').read()
            html_url = DEFAULT_FILEPATH + full_fname

            html_sailer = Sailer()
            html_sailer.go(html_url)
            # text = html_sailer.driver.find_element_by_xpath(r'/html/body').text
            # print(text)

            file_name = fname.split(".")[0]
            file_name = file_name.replace("_", " ")
            print(file_name)
            es.create(index="policy", doc_type="_doc", id=uuid.uuid4(),
                      body={"title": file_name, "content_html": html, "hit": 0})


def split_policy():
    sailer = Sailer()
    sailer.go(
        "file:///C:/Users/nj/PycharmProjects/TestModule/new_policy_html/3%ED%92%88%EC%9D%B8%EC%A6%9D%EC%A0%9C.html")
    head_html = sailer.xpath('/html/head').get_attribute('innerHTML')
    body_html = sailer.xpath('/html/body').get_attribute('innerHTML')
    titles = re.findall('(<p.*><img src=".*M1x1GvQUIK2qa0SsrWtdb99T\/\/Z".*<\/p>)\s*((.*\s*)*)', body_html)
    print(titles)
    for title in titles:
        print(title)

    # result_html = "\n".join(["<html><head>", head_html, "</head>", "<body>", *titles, "</body></html>"])
    #
    # f = open("test.html", 'w', encoding='UTF8')
    # f.write(result_html)
    # f.close()


# split_policy()

def convert_pdf_to_html():
    file_path = "C:/Users/nj/PycharmProjects/TestModule/policy_html/{}"
    new_file_path = "C:/Users/nj/PycharmProjects/TestModule/new_policy_html/{}"
    for root, dirs, files in os.walk('policy_html'):
        for fname in files:
            full_fname = os.path.join(root, fname)
            if full_fname.endswith("htm"):
                html = open(full_fname, encoding="UTF8").read()
                html_sailer = Sailer()

                file = full_fname.split('\\')[1]
                print(file)
                html_sailer.go(file_path.format(file))

                file_name = ""

                for i in range(10):
                    text = html_sailer.driver.find_element_by_class_name("p{}".format(i)).text
                    if "." in text:
                        file_name = text.split(".")[1].strip().replace(" ", "_").replace("/", "+")
                        break
                print(file_name)
                os.renames(file_path.format(file), new_file_path.format(".".join([file_name, "html"])))
