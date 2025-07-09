import scrapy
import re

BASE_URL = 'http://en.wikipedia.org'

class NWinnerItemBio(scrapy.Item):
    link = scrapy.Field()
    name = scrapy.Field()
    gender = scrapy.Field()
    mini_bio = scrapy.Field()
    image_urls = scrapy.Field()
    bio_image = scrapy.Field()
    images = scrapy.Field()

class NWinnerSpiderBio(scrapy.Spider):
    
    name = 'nwinners_minibio'
    allowed_domains = ['en.wikipedia.org']
    start_urls = [
        "http://en.wikipedia.org/wiki/List_of_Nobel_laureates_by_country"
    ]

    def parse(self, response):

        filename = response.url.split('/')[-1]
        h3s = response.xpath('//h3')
        items = []
        for h3 in h3s:
            country = h3.xpath('./text()').get()
            if country:
                winners = h3.xpath('../following-sibling::ol[1]')
                for w in winners.xpath('li'):
                    wdata = {}
                    wdata['link'] = BASE_URL + w.xpath('a/@href').extract()[0]
                    # Processar a página biográfica do ganhador com o método get_mini_bio
                    request = scrapy.Request(
                        wdata['link'], callback=self.get_mini_bio)
                    request.meta['item'] = NWinnerItemBio(**wdata)
                    yield request
                    
    def get_mini_bio(self, response):
        """ Get the winner's bio text and photo """

        BASE_URL_ESCAPED = 'http:\/\/en.wikipedia.org'
        item = response.meta['item']
        item['name'] = response.css('h1::text').get() or item['link'].split('/')[-1].replace('_', ' ')
        item['image_urls'] = []
        img_src = response.xpath('//table[contains(@class, "infobox")]//img/@src')
        if img_src:
            item['image_urls'] = ['https:' + img_src[0].extract()]
        
        ps = response.xpath('//table[contains(@class, "infobox")]/following-sibling::*[not(self::h2)][preceding-sibling::table[contains(@class, "infobox")]][self::p]').extract()

        # Concatena os parágrafos da biografia para uma string mini_bio
        mini_bio = ''
        for p in ps:
            mini_bio += p
        # corrige para links wiki
        mini_bio = mini_bio.replace('href="/wiki', 'href="' + BASE_URL + '/wiki"')
        mini_bio = mini_bio.replace('href="#', 'href="' + item['link'] + '#"')
        item['mini_bio'] = mini_bio

        item['name'] = response.xpath('//h1/text()').get() or item['link'].split('/')[-1].replace('_', ' ')

        text = ' '.join(response.xpath('//p//text()').getall()).lower()
        if any(word in text for word in [' she ', ' her ', ' actress ', ' born as a girl ']):
            item['gender'] = 'female'
        elif any(word in text for word in [' he ', ' his ', ' actor ', ' born as a boy ']):
            item['gender'] = 'male'
        else:
            item['gender'] = 'unknown'

        yield item

