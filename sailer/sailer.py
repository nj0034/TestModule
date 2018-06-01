from selenium import webdriver

from sailer.sentry import SailerLogger


class Sailer:
    def __init__(self):
        super().__init__()

        # default timeout
        self._timeout = 10

        # initialize driver
        self.driver = webdriver.PhantomJS(executable_path=r'C:\Users\nj\Downloads\phantomjs-2.1.1-windows\bin/phantomjs')
        self.driver.implicitly_wait(self.timeout)

        # get sentry logger
        self.logger = SailerLogger()
        self.logger.sentry.user_context({
            'sailer name': self.__class__.__name__,
        })

    def close(self):
        return self.driver.close()

    def log(self, message):
        print("PLEASE USE print FUNCTION. DO NOT USE self.log() ANYMORE!")
        print(message)

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, seconds):
        self._timeout = seconds

    @property
    def html(self):
        return self.driver.page_source

    @property
    def current_url(self):
        return self.driver.current_url

    def go(self, url):
        return self.driver.get(url)

    def id(self, id_):
        return self.driver.find_element_by_id(id_=id_)

    def css(self, css_selector):
        return self.driver.find_element_by_css_selector(css_selector=css_selector)

    def xpath(self, xpath):
        return self.driver.find_element_by_xpath(xpath=xpath)

    def ids(self, id_):
        return self.driver.find_elements_by_id(id_=id_)

    def csss(self, css_selector):
        return self.driver.find_elements_by_css_selector(css_selector=css_selector)

    def xpaths(self, xpath):
        return self.driver.find_elements_by_xpath(xpath=xpath)

    def wait_css(self, css_selector):
        try:
            if self.css(css_selector):
                return True
        except Exception:
            pass
        finally:
            return False

    def wait_xpath(self, xpath):
        try:
            if self.xpath(xpath):
                return True
        except Exception:
            pass
        finally:
            return False

    def wait_id(self, id_):
        try:
            if self.id(id_):
                return True
        except Exception:
            pass
        finally:
            return False
