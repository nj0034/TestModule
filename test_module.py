from sailer.sailer import Sailer
from sailer.utils import *
import random
import time
import re
import urllib.parse
import json
from elasticsearch import Elasticsearch

json_data = open('json\대티즌.json', encoding='UTF8').read()
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
        page_url_list = self.rule.get('page_url_list', '')

        if not page_url_list:
            page_url_list = [self.rule['page_url']]

        for page_url in page_url_list:
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
            es.index(index="skku-notice-test", doc_type="_doc", body=parsing_result_json_list[0])

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
        # href 안에서 파라미터만 추출해서 base_url form 에 넣어서 생성
        param_regex = self.props['title_url']['param_regex']
        if param_regex:
            base_url = self.props['title_url']['base_url']
            title_url_list = self.combine_url_with_params(param_regex, href_list, base_url)

            parsing_result_json_list = [{"url": title_url} for title_url in title_url_list]

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

                regex = self.props[in_prop].get('regex', '')
                class_name = self.props[in_prop].get('class_name', '')

                # 정규표현식
                if regex:
                    html = self.xpath(self.props[in_prop]['xpath']).get_attribute('innerHTML')
                    in_prop_json = self.parsing_regex_prop(in_prop, regex, html)

                # class name
                elif class_name:
                    web_element = self.driver.find_element_by_class_name(class_name)
                    in_prop_json = self.parsing_prop(prop=in_prop, web_element=web_element)

                # xpath
                else:
                    in_prop_json = self.parsing_prop(prop=in_prop)

                parsing_result_json.update(in_prop_json)

        return parsing_result_json_list

    def parsing_prop(self, **kwargs):
        prop = kwargs.get('prop', '')
        prop_info = self.props[prop]

        xpath = prop_info['xpath']

        web_element = kwargs.get('web_element', '')

        if not web_element:
            try:
                web_element = self.xpath(xpath)
                web_elements = self.xpaths(xpath)
            except:
                web_element = None
                web_elements = None

        prop_type = prop_info['type']

        if web_element or web_elements:
            if prop_type == 'content':
                prop_json = {
                    "content_text": web_element.text,
                    "content_HTML": web_element.get_attribute('innerHTML'),
                }
            elif prop_type == 'date':
                date = web_element.text
                date = date.replace('오전', 'AM')
                date = date.replace('오후', 'PM')

                format = prop_info['format']
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
                attach_name_list = list()
                href_list = [urllib.parse.unquote(web_element.get_attribute('href')) for web_element in web_elements if
                             web_element]
                param_regex = prop_info['param_regex']

                if param_regex:
                    # param_list = [re.findall(prop_info['param_regex'], href) for href in href_list]
                    #
                    # for param in param_list:
                    #     attach_url_list.append(prop_info['base_url'].format(*param))
                    base_url = prop_info['base_url']
                    attach_url_list = self.combine_url_with_params(param_regex, href_list, base_url)

                else:
                    attach_url_list = href_list

                if attach_url_list:
                    if prop_info.get('splited', ''):
                        attach_name_list = [
                            re.compile(prop_info['name_regex']).search(web_element.get_attribute('innerHTML')).group(1)
                            for web_element in self.xpaths(prop_info['HTML_xpath'])]
                    else:
                        attach_name_list = re.findall(prop_info['name_regex'],
                                                      self.xpath(prop_info['HTML_xpath']).get_attribute('innerHTML'))

                # s3에 저장하는 함수 넣기 + s3 url list 만들기
                attach_s3_url_list = list()

                prop_json = {
                    "attach": [{
                        "url": url,
                        "name": name,
                    } for url, name in zip(attach_url_list, attach_name_list)]}

                # prop_json = {
                #     # "attach": attach_s3_url_list
                #     "attach_url": attach_url_list,
                #     "attach_name": attach_name_list
                # }
            else:
                prop_json = {
                    prop: web_element.text
                }
            print(prop_json)

        else:
            prop_json = {}
            print(prop, "has no element")

        return prop_json

    def parsing_regex_prop(self, prop, regex, html):
        prop_data = re.compile(regex).search(html).group(1)

        if self.props[prop]['type'] == 'date':
            format = self.props[prop]['format']
            prop_data = convert_datetime(prop_data, format, '%Y-%m-%d %H:%M:%S')

        prop_json = {prop: prop_data}
        print(prop_json)
        return prop_json

    @staticmethod
    def combine_url_with_params(param_regex, href_list, base_url):
        url_list = list()
        param_list = [re.findall(param_regex, href) for href in href_list]

        for param in param_list:
            param = param[0]
            if isinstance(param, tuple):
                url_list.append(base_url.format(*param))
            else:
                url_list.append(base_url.format(param))

        return url_list


test_module = TestModule()
test_module.start()
test_module.close()
