import logging
import argparse
import sys
import time
from contextlib import contextmanager
from logging import handlers

import bs4
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.chrome.options import Options

import uuid

import dateparser

from datetime import datetime

CSS_SELECTORS = {
    'POST': 'div.Post',
    'VOTE_COUNT': '._1rZYMD_4xY3gRcSS3p8ODO',
    'COMMENT_COUNT': 'span.FHCV02u6Cp2zYL0fhQPsO',
    'CAKE_DAY': 'span#profile--id-card--highlight-tooltip--cakeday',
    'USER_KARMA': 'span#profile--id-card--highlight-tooltip--karma',
    'CATEGORY': 'div._2mHuuvyV9doV3zwbZPtIPG > a._3ryJoIoycVkA88fy40qNJc',
    'POST_DATE': 'div._2J_zB4R1FH2EjGMkQjedwc',
    'POST_HOVER_DATE': 'a._3jOxDPIQ0KaOWpzvSQo-1s',
    'POST_LINK': 'a._3jOxDPIQ0KaOWpzvSQo-1s',
    'USER': 'a._2tbHP6ZydRpjI44J3syuqC._23wugcdiaj44hdfugIAlnX.oQctV4n0yUb0uiHDdGnmE',
    'USER_CARD': 'div._3uK2I0hi3JFTKnMUFHD2Pd',
    'CARD_KARMA': 'div._18aX_pAQub_mu1suz4-i8j',
    'USERNAME': 'h1._3LM4tRaExed4x1wBfK1pmg',
}

LOGMODES = {
    'ALL': (logging.DEBUG, logging.INFO, logging.ERROR, logging.WARNING, logging.CRITICAL, logging.NOTSET),
    'ERROR': (logging.ERROR,),
    'WARNING': (logging.WARNING,),
    'DISABLE': (),
}


def get_element_text(driver, css_selector):
    return WebDriverWait(driver, 10) \
        .until(ec.presence_of_element_located((By.CSS_SELECTOR, css_selector))) \
        .get_attribute('innerText')


def show_element(driver, css_selector):
    element = WebDriverWait(driver, 10).until(ec.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
    ActionChains(driver).move_to_element(element).perform()


def post_count_validator(arg):
    try:
        i = int(arg)
    except ValueError:
        raise argparse.ArgumentTypeError("The argument must be an integer")
    if i < 0:
        raise argparse.ArgumentTypeError(f"The argument must be > {0}")
    return i


def logmode_validator(arg):
    if arg in ['ALL', 'ERROR', 'WARNING', 'DISABLE']:
        return arg
    raise argparse.ArgumentTypeError("Unknown mode")


@contextmanager
def open_webdriver():
    driver = init_driver()
    try:
        yield driver
    finally:
        driver.quit()


@contextmanager
def open_tab(driver, url):
    parent_handler = driver.window_handles[0]
    driver.execute_script("window.open('');")
    logging.info(f'New tab is opened with url: {url}')
    all_handlers = driver.window_handles
    new_handler = [x for x in all_handlers if x != parent_handler][0]
    driver.switch_to.window(new_handler)
    driver.get(url)
    try:
        yield
    finally:
        driver.close()
        logging.info('Tab is closed')
        driver.switch_to.window(parent_handler)


class StdoutFilter(logging.Filter):

    def __init__(self, logmode):
        self.logmode = logmode

    def filter(self, record):
        return record.levelno in self.logmode


def init_logger(logmode):
    format = '%(asctime)s - %(levelname)s - %(message)s'
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)

    format = logging.Formatter(format)

    ch = logging.StreamHandler(sys.stdout)
    ch.addFilter(StdoutFilter(LOGMODES[logmode]))
    ch.setFormatter(format)
    log.addHandler(ch)

    fh = handlers.RotatingFileHandler('app.log')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(format)
    log.addHandler(fh)


def init_driver():
    options = Options()
    prefs = {'profile.default_content_setting_values': {'images': 2}}
    options.add_experimental_option('prefs', prefs)
    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")
    options.add_argument("--disable-extensions")
    # options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    logging.debug('WebDriver is initialized')
    return driver


def save(parsed_posts):
    with open(f'{datetime.today().strftime("reddit-%Y%m%d%H%M")}.txt', "w") as file:
        file.writelines([';'.join(parsed_post.values()) + '\n' for parsed_post in parsed_posts])
        logging.info(f'Successful saved to {file.name}')


def parse_post(post, parsed_posts):
    parsed_post = {}
    parsed_post['unique_id'] = str(uuid.uuid1())
    parsed_post['url'] = post.find_element_by_css_selector(CSS_SELECTORS['POST_LINK']).get_attribute('href')
    user_url = post.find_element_by_css_selector(CSS_SELECTORS['USER']).get_attribute('href')
    if get_user_info(driver, parsed_post, user_url):
        parsed_posts.append(parsed_post)
        get_post_info(post, parsed_post)
        logging.info(f'Successfully parse: {len(parsed_posts)}')


def lookup(driver, count):
    logging.info(f'Parse is starting with count: {count}')
    driver.get('https://www.reddit.com/top/?t=month')
    index = 0
    parsed_posts = []
    while len(parsed_posts) < count:
        posts = driver.find_elements_by_css_selector(CSS_SELECTORS['POST'])
        posts = posts[index:len(posts)]
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        for post in posts:
            parse_post(post, parsed_posts)
            index += 1
            if (len(parsed_posts)) == count:
                break
    return parsed_posts


def get_post_date(driver):
    post_date = get_element_text(driver, CSS_SELECTORS['POST_HOVER_DATE'])
    return dateparser.parse(post_date).strftime("%Y-%m-%d")


def get_post_info(post, parsed_post):
    parsed_post['post_date'] = get_post_date(post)
    parsed_post['comment_count'] = get_element_text(post, CSS_SELECTORS['COMMENT_COUNT']).split(' ')[0]
    parsed_post['vote_count'] = get_element_text(post, CSS_SELECTORS['VOTE_COUNT'])
    parsed_post['category'] = get_element_text(post, CSS_SELECTORS['CATEGORY']).split('/')[1]


def get_user_info(driver, parsed_post, user_url):
    with open_tab(driver, user_url):
        try:
            parsed_post['username'] = user_url.split('/')[-2]
            parsed_post['user_karma'] = get_element_text(driver, CSS_SELECTORS['USER_KARMA'])
            parsed_post['cake_day'] = get_element_text(driver, CSS_SELECTORS['CAKE_DAY'])
            show_element(driver, CSS_SELECTORS['USER_KARMA'])
            karma = get_element_text(driver, CSS_SELECTORS['USER_CARD']).split('\n')
            parsed_post['post_karma'] = karma[0].split(' ')[0]
            parsed_post['comment_karma'] = karma[1].split(' ')[0]
            return True
        except TimeoutException:
            return False


if __name__ == '__main__':
    start = datetime.now()
    parser = argparse.ArgumentParser(description='Reddit parser')
    parser.add_argument('--count', required=False, default=100, type=post_count_validator,
                        help='Count of post to parse')
    parser.add_argument('--logmode', required=False, default='ALL', type=logmode_validator,
                        help='Log mode  - ALL - all levers, ERROR - only ERROR lever, WARNING - only WARNING lever, DISABLE - no console console log')
    args = parser.parse_args()
    init_logger(args.logmode)
    try:
        with open_webdriver() as driver:
            parsed_posts = lookup(driver, args.count)
            save(parsed_posts)
            logging.debug(f'The duration of the scraping: {datetime.now() - start}')
    except WebDriverException as e:
        logging.error(e)