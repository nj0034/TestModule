from sailer.sailer import Sailer
from sailer.pacific import *
from sailer.utils import *
import random
import time
import re
import urllib.parse
import json
from elasticsearch import Elasticsearch

json_data = open('json\문과.json', encoding='UTF8').read()
XPATH_JSON = json.loads(json_data)
es = Elasticsearch('https://search-toast-rgeq2lspq63rey535bxmff5m4y.ap-northeast-2.es.amazonaws.com')


class TestModule(Sailer):
    def start(self):
        self.meta = XPATH_JSON['meta']
        self.parser = XPATH_JSON['parser']
        self.rule = XPATH_JSON['rule']
        self.props = self.rule['properties']
        self.top = False

        method = self.parser['method']
        page_url = self.rule['page_url']

        if method == 'url_based':
            start_page = int(self.rule['start_page'])
            page_increase = int(self.rule['page_increase'])

            for i in range(start_page, 100):
                self.go(page_url.format(page=i * page_increase))
                print("# {} page start".format(i))
                self.url_based()

        elif method == 'next_button':
            self.go(page_url)
            self.next_button()

        else:
            pass

    def next_button(self):
        in_prop_list = self.props.keys()
        # top_article_url = self.xpath(XPATH_JSON['top_article_xpath']).get_attribute('href')
        # self.go(top_article_url)
        self.wait_xpath(self.rule['top_article_xpath'])
        self.xpath(self.rule['top_article_xpath']).click()
        # self.go('http://cs.skku.edu/open/notice/view/2253')

        while (True):
            parsing_result_json_list = [{"url": self.current_url}]
            parsing_result_json_list = self.parsing_in_props(in_prop_list, parsing_result_json_list)
            print(parsing_result_json_list)

            # es에 parsing_result_json_list 저장(top 글이면 저장 안함)
            es.index(index="content", doc_type="_doc", body=parsing_result_json_list[0])

            next_button_url = self.xpath(self.rule['next_button_xpath']).get_attribute('href')
            if next_button_url:
                self.go(next_button_url)
            else:
                break

    def url_based(self):
        out_prop_list = list()
        in_prop_list = list()
        for key, value in self.props.items():
            if value['position'] == 'out':
                out_prop_list.append(key)
            elif value['position'] == 'in':
                in_prop_list.append(key)
            else:
                pass

        title_url_web_elements = self.xpaths(self.props['title_url']['xpath'])
        href_list = [title_url_web_element.get_attribute('href') for title_url_web_element in title_url_web_elements]

        # 자바스크립트 url
        if self.props['title_url']['param_regex']:
            param_list = [re.findall(self.props['title_url']['param_regex'], href) for href in href_list]
            for param in param_list:
                if isinstance(param, tuple):
                    parsing_result_json_list = [{"url": self.props['title_url']['base_url'].format(*param)}]
                else:
                    parsing_result_json_list = [{"url": self.props['title_url']['base_url'].format(param)}]

        # 보통 url
        else:
            parsing_result_json_list = [{"url": href} for href in href_list]

        # 리스트에서 파싱해야 하는 props
        for out_prop in out_prop_list:
            web_elements = self.xpaths(self.props[out_prop]['xpath'])
            for web_element, parsing_result_json in zip(web_elements, parsing_result_json_list):
                out_prop_json = self.parsing_prop(prop=out_prop, web_element=web_element)
                parsing_result_json.update(out_prop_json)

        parsing_result_json_list = self.parsing_in_props(in_prop_list, parsing_result_json_list)

        # es에 저장(top 글이면 저장 안함)
        for parsing_result_json in parsing_result_json_list:
            es.index(index="content", doc_type="_doc", body=parsing_result_json)
            print(parsing_result_json)

        time_interval = [int(n) for n in self.parser['interval'].split('-')]
        random_time = random.randint(*time_interval)

        time.sleep(random_time)

        self.top = True

    def parsing_in_props(self, in_prop_list, parsing_result_json_list):
        for parsing_result_json in parsing_result_json_list:
            self.go(parsing_result_json['url'])
            for in_prop in in_prop_list:
                if self.props[in_prop].get('regex', ''):
                    regex = self.props[in_prop]['regex']
                    html = self.xpath(self.props[in_prop]['xpath']).get_attribute('innerHTML')

                    in_prop_json = self.parsing_regex_prop(in_prop, regex, html)
                else:
                    in_prop_json = self.parsing_prop(prop=in_prop)

                parsing_result_json.update(in_prop_json)

        return parsing_result_json_list

    def parsing_prop(self, **kwargs):
        prop = kwargs.get('prop', '')
        xpath = self.props[prop]['xpath']

        web_element = kwargs.get('web_element', '')

        if not web_element:
            try:
                web_element = self.xpath(xpath)
            except:
                web_element = None

        web_elements = self.xpaths(xpath)

        prop_type = self.props[prop]['type']

        if prop_type == 'content':
            prop_json = {
                "content_text": web_element.text,
                "content_HTML": web_element.get_attribute('innerHTML'),
            }
        elif prop_type == 'date':
            date = web_element.text
            date = date.replace('오전', 'AM')
            date = date.replace('오후', 'PM')

            format = self.props[prop]['format']
            date = convert_datetime(date, format, '%Y-%m-%d %H:%M:%S')
            prop_json = {
                "created_datetime": date
            }
        elif prop_type == 'image':
            img_url_list = [web_element.get_attribute('src') for web_element in web_elements if web_element]

            # s3에 저장하는 함수 넣기 + s3 url list 만들기
            img_s3_url_list = list()

            prop_json = {
                # "img": img_s3_url_list
                "img": img_url_list
            }
        elif prop_type == 'file':
            attach_url_list = list()
            attach_name_list = list()
            href_list = [urllib.parse.unquote(web_element.get_attribute('href')) for web_element in web_elements if web_element]

            if self.props[prop]['param_regex']:
                param_list = [re.findall(self.props[prop]['param_regex'], href) for href in href_list]

                for param in param_list:
                    # if isinstance(param, tuple):
                    #     attach_url_list.append(self.props[prop]['base_url'].format(*param))
                    # else:
                    #     attach_url_list.append(self.props[prop]['base_url'].format(param))
                    attach_url_list.append(self.props[prop]['base_url'].format(*param))

            else:
                attach_url_list = href_list

            if attach_url_list:
                attach_name_list = re.findall(self.props[prop]['name_regex'],
                                              self.xpath(self.props[prop]['HTML_xpath']).get_attribute('innerHTML'))

            # s3에 저장하는 함수 넣기 + s3 url list 만들기
            attach_s3_url_list = list()

            prop_json = {
                # "attach": attach_s3_url_list
                "attach_url": attach_url_list,
                "attach_name": attach_name_list
            }
        else:
            prop_json = {
                prop: web_element.text
            }

        print(prop_json)
        return prop_json

    def parsing_regex_prop(self, prop, regex, html):
        prop_json = {prop: re.findall(regex, html)}
        return prop_json


test_module = TestModule()
test_module.start()
test_module.close()
