import scrapy
import re

BASE_URL = 'http://en.wikipedia.org'

class NWinnerItem(scrapy.Item):
    name = scrapy.Field()
    link = scrapy.Field()
    mini_bio = scrapy.Field()
    year = scrapy.Field()
    category = scrapy.Field()
    country = scrapy.Field()
    gender = scrapy.Field()
    born_in = scrapy.Field()
    date_of_birth = scrapy.Field()
    date_of_death = scrapy.Field()
    place_of_birth = scrapy.Field()
    place_of_death = scrapy.Field()
    text = scrapy.Field()


class NWinnerSpider(scrapy.Spider):
    name = 'nwinners_full'
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
                    wdata = process_winner_li(w, country)
                    request = scrapy.Request(
                        wdata['link'], callback=self.parse_bio, dont_filter=True)
                    request.meta['item'] = NWinnerItem(**wdata)
                    yield request
                    # yield NWinnerItem(**wdata)

    def parse_bio(self, response):
        item = response.meta['item']
        href = response.xpath("//li[@id='t-wikibase']/a/@href").extract()
        if href:
            # Wikipedia have changed the wikibase URL to include the 'https:' leader
            # url = 'https:' + href[0]
            url = href[0]
            wiki_code = url.split('/')[-1]
            url = 'https://wikidata.org/wiki/' + wiki_code
            request = scrapy.Request(url,
                                     callback=self.parse_wikidata,
                                     dont_filter=True)
            request.meta['item'] = item
            yield request

    def parse_wikidata(self, response):
        item = response.meta['item']
        property_codes = [
            {'name': 'date_of_birth', 'code': 'P569'},
            {'name': 'date_of_death', 'code': 'P570'},
            {'name': 'place_of_birth', 'code': 'P19', 'link': True},
            {'name': 'place_of_death', 'code': 'P20', 'link': True},
            {'name': 'gender', 'code': 'P21', 'link': True}
        ]

        for prop in property_codes:

            link_html = ''
            if prop.get('link'):
                link_html = '/a'

            code_block = response.xpath('//*[@id="%s"]' % (prop['code']))
            # continue if the code_block exists
            if code_block:
                # We can use the css selector, which has superior class selection
                values = code_block.css('.wikibase-snakview-value')
            # the first value corresponds to the code property (e.g. '10 August 1879')
                value = values[0]
                prop_sel = value.xpath('.%s/text()' % link_html)
                if prop_sel:
                    item[prop['name']] = prop_sel[0].extract()

        yield item

def get_persondata(table, item):
    fields = ['Date of birth', 'Place of birth',
              'Date of death', 'Place of death']
    for tr in table.xpath('tr'):
        label = tr.xpath('td[@class="persondata-label"]/text()').extract()
        if label and label[0] in fields:
            text = ' '.join(
                tr.xpath('td[not(@class)]/descendant-or-self::text()').extract())
            print(text)
            item[label[0].lower().replace(' ', '_')] = text


def guess_gender(text, threshold=0):
    import re

    he = len(list(re.finditer(' he ', text)))
    she = len(list(re.finditer(' she ', text)))
    diff = she - he

    print('she %d, he %d, diff %d' % (she, he, diff))
    if diff > threshold:
        return 'female'
    elif diff < -threshold:
        return 'male'
    else:
        return None

def process_winner_li(w, country=None):
    """
    Process a winner's <li> tag, adding country of birth or nationality,
    as applicable.
    """
    wdata = {}
    # get the href link-adress from the <a> tag
    wdata['link'] = BASE_URL + w.xpath('a/@href').extract()[0]
    text = ' '.join(w.xpath('descendant-or-self::text()').extract())
    # we use the comma-delimited text-elements, stripping whitespace from
    # the ends.
    # split the text at the commas and take the first (name) string
    wdata['name'] = text.split(',')[0].strip()

    year = re.findall('\d{4}', text)
    if year:
        wdata['year'] = int(year[0])
    else:
        wdata['year'] = 0
        print('Oops, no year in ', text)

    category = re.findall(
        'Physics|Chemistry|Physiology or Medicine|Literature|Peace|Economics',
        text)
    if category:
        wdata['category'] = category[0]
    else:
        wdata['category'] = ''
        print('Oops, no category in ', text)

    if country:
        if text.find('*') != -1:
            wdata['country'] = ''
            wdata['born_in'] = country
        else:
            wdata['country'] = country
            wdata['born_in'] = ''

    # store a copy of the link's text-string for any manual corrections
    wdata['text'] = text
    return wdata