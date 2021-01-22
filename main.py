import logging
import time

from bs4 import BeautifulSoup
from urllib3 import HTTPConnectionPool

from logger_conf import configurate_logger

import argparse

from contextlib import contextmanager

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

import requests

from validators import unsigned_int_validator, logmode_validator

PORT = 8087
HOSTNAME = 'localhost'

CSS_SELECTORS = {
    'POST': 'div.Post',
    'VOTE_COUNT': '._1rZYMD_4xY3gRcSS3p8ODO',
    'COMMENT_COUNT': 'span.FHCV02u6Cp2zYL0fhQPsO',
    'CAKE_DAY': 'span#profile--id-card--highlight-tooltip--cakeday',
    'USER_KARMA': 'span._1hNyZSklmcC7R_IfCUcXmZ',
    'CATEGORY': 'div._2mHuuvyV9doV3zwbZPtIPG > a._3ryJoIoycVkA88fy40qNJc',
    'POST_DATE': 'div._2J_zB4R1FH2EjGMkQjedwc',
    'POST_HOVER_DATE': 'a._3jOxDPIQ0KaOWpzvSQo-1s',
    'POST_LINK': 'a._3jOxDPIQ0KaOWpzvSQo-1s',
    'USER': 'a._2tbHP6ZydRpjI44J3syuqC._23wugcdiaj44hdfugIAlnX.oQctV4n0yUb0uiHDdGnmE',
    'USER_CARD': 'div._m7PpFuKATP9fZF4xKf9R',
    'CARD_KARMA': '_18aX_pAQub_mu1suz4-i8j',
    'USERNAME': 'h1._3LM4tRaExed4x1wBfK1pmg',
}




def get_element_text(driver, css_selector):
    return WebDriverWait(driver, 10) \
        .until(ec.presence_of_element_located((By.CSS_SELECTOR, css_selector))) \
        .get_attribute('innerText')


def show_element(driver, css_selector):
    element = WebDriverWait(driver, 10).until(ec.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
    ActionChains(driver).move_to_element(element).perform()


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


def init_driver():
    options = Options()
    prefs = {'profile.default_content_setting_values': {'images': 2}}
    options.add_experimental_option('prefs', prefs)
    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    logging.debug('WebDriver is initialized')
    return driver


def save(parsed_post):
    requests.post(f'http://{HOSTNAME}:{PORT}/posts/', json=parsed_post)


def parse_post(post, post_link, user_link, parsed_posts):
    parsed_post = {}
    parsed_post['unique_id'] = str(uuid.uuid1())
    parsed_post['url'] = post_link
    if get_user_info(driver, parsed_post, user_link):
        parsed_posts.append(parsed_post)
        get_post_info(driver, post, parsed_post)
        save(parsed_post)
        logging.info(f'Successfully parse: {len(parsed_posts)}')


def lookup(driver, count):
    logging.info(f'Parse is starting with count: {count}')
    driver.get('https://www.reddit.com/top/?t=month')
    index = 0
    parsed_posts = []
    while len(parsed_posts) < count:
        post_links = driver.find_elements_by_css_selector(CSS_SELECTORS['POST_LINK'])
        user_links = driver.find_elements_by_css_selector(CSS_SELECTORS['USER'])
        posts = driver.find_elements_by_css_selector(CSS_SELECTORS['POST'])
        min_len = min(len(post_links), len(user_links), len(posts))
        post_links = post_links[index:min_len]
        user_links = user_links[index:min_len]
        posts = posts[index:min_len]
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        for i, post in enumerate(posts):
            parse_post(post, post_links[i].get_attribute('href'), user_links[i].get_attribute('href'), parsed_posts)
            index += 1
            if (len(parsed_posts)) == count:
                break


def get_post_date(driver):
    post_date = get_element_text(driver, CSS_SELECTORS['POST_HOVER_DATE'])
    return dateparser.parse(post_date).strftime("%Y-%m-%d")


def get_post_info(driver, post, parsed_post):
    with open_tab(driver, parsed_post['url']):
        show_element(driver, CSS_SELECTORS['USER'])
        WebDriverWait(driver, 10).until(ec.visibility_of_element_located((By.CSS_SELECTOR, CSS_SELECTORS['USER_CARD'])))
        html = driver.page_source
        soup = BeautifulSoup(html)
        post_karma, comment_karma = (elem.text for elem in soup.find_all(class_=CSS_SELECTORS['CARD_KARMA']))
        parsed_post['post_karma'] = post_karma
        parsed_post['comment_karma'] = comment_karma
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
            return True
        except TimeoutException:
            return False


if __name__ == '__main__':
    start = datetime.now()

    parser = argparse.ArgumentParser(description='Reddit parser')
    parser.add_argument('--count',
                        required=False,
                        default=100,
                        type=unsigned_int_validator,
                        help='Count of post to parse')
    parser.add_argument('--logmode',
                        required=False,
                        default='ALL',
                        type=logmode_validator,
                        help="""Log mode  
                                - ALL - all levers, 
                                ERROR - only ERROR lever, 
                                WARNING - only WARNING lever, 
                                DISABLE - no console console log""")
    args = parser.parse_args()

    configurate_logger(args.logmode)
    try:
        with open_webdriver() as driver:
            lookup(driver, args.count)
            logging.debug(f'The duration of the scraping: {datetime.now() - start}')
    except WebDriverException as e:
        logging.error(e)
    except HTTPConnectionPool:
        logging.error(f'Сan\'t connect to the server. {HOSTNAME}:{PORT}')
