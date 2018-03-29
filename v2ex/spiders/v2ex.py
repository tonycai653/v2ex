import scrapy
import base64
import json
from urllib.parse import urlparse


class V2exSpider(scrapy.Spider):
    name = 'qiniu-info'

    user_name = 'tonycai653'
    password = '123qwe!@#'

    start_urls = ['https://www.v2ex.com']

    def parse(self, response):
        yield from self._parse(response)
    #def parse(self, response):
    #    login_url = 'https://www.v2ex.com/signin'
    #    yield response.follow(login_url, self._get_captcha)

    def _get_captcha(self, response):
        cap_href = response.xpath('//div[contains(@style, "background-image")]/@style').re_first(
                                  r'url\(\'(/_captcha\?once=\d+)\'\)')
        req = response.follow(cap_href, callback=self._recognize_captcha)
        inputs = response.xpath('//form[@method="post"]//input/@name').extract()
        self.logger.info(inputs)
        req.meta['inputs'] = inputs
        yield req

    def _recognize_captcha(self, response):
        once = urlparse(response.url).query.split('=')[-1]
        reg_url = 'http://op.juhe.cn/vercode/index'
        with open('captcha.png', 'wb') as f:
            f.write(response.body)

        req = scrapy.FormRequest(reg_url, formdata={
            'key': '23c83fd99b4778a9092f4b7fbff65f98',
            'codeType': '8001',
            'base64Str': base64.b64encode(response.body),
        }, callback=self._login)
        req.meta['once'] = once
        req.meta['inputs'] = response.meta['inputs']
        yield req

    def _login(self, response):
        json_data = json.loads(response.text)
        result = json_data['result']
        self.logger.info('captcha: %s' % result)
        headers = {
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.v2ex.com',
        }

        inputs = response.meta['inputs']
        yield scrapy.FormRequest('https://www.v2ex.com/signin', formdata={
            'next': '/',
            'once': response.meta['once'],
            inputs[0]: self.user_name,
            inputs[1]: self.password,
            inputs[2]: result,
        }, callback=self._get_pages)

    def _get_pages(self, response):
        href = response.xpath('//a[@href="/recent"]/@href').extract_first()
        yield response.follow(href, callback=self._parse_all)

    def _parse_all(self, response):
        max_page = response.xpath('//input[@type="number"]/@max').extract_first()
        for page_num in range(int(max_page)):
            page_url = response.url + "?p={}".format(page_num)
            yield response.follow(page_url, callback=self._parse)

    def _parse(self, response):
        lks = response.xpath('//span[@class="item_title"]/a')
        for le in lks:
            href = le.xpath('./@href').extract_first()
            title = le.xpath('./text()').extract_first()
            url = response.urljoin(href)
            self.logger.info('%s %s' % (title, url))
            title = self.filter(title)
            if title and href:
                yield {
                    'href': href,
                    'title': title,
                }

    @staticmethod
    def filter(text, filterby='七牛'):
        if filterby in text:
            return text
