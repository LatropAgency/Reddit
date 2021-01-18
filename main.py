import logging
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

CSS_SELECTORS = {
    'VOTE_COUNT': '._1rZYMD_4xY3gRcSS3p8ODO',
    'COMMENT_COUNT': 'span.FHCV02u6Cp2zYL0fhQPsO',
    'CAKE_DAY': 'span#profile--id-card--highlight-tooltip--cakeday',
    'USER_KARMA': 'span#profile--id-card--highlight-tooltip--karma',
    'CATEGORY': 'span._19bCWnxeTjqzBElWZfIlJb',
    'POST_DATE': 'div._2J_zB4R1FH2EjGMkQjedwc',
    'POST_HOVER_DATE': 'a._3jOxDPIQ0KaOWpzvSQo-1s',
    'POST_LINK': 'a._3jOxDPIQ0KaOWpzvSQo-1s',
    'USER': 'a._2tbHP6ZydRpjI44J3syuqC._23wugcdiaj44hdfugIAlnX.oQctV4n0yUb0uiHDdGnmE',
    'USER_CARD': 'div._m7PpFuKATP9fZF4xKf9R',
    'CARD_KARMA': 'div._18aX_pAQub_mu1suz4-i8j',
}


def get_element_text(driver, css_selector):
    return WebDriverWait(driver, 10) \
        .until(ec.presence_of_element_located((By.CSS_SELECTOR, css_selector))) \
        .get_attribute('innerHTML')


def show_element(driver, css_selector):
    element = driver.find_element_by_css_selector(css_selector)
    ActionChains(driver).move_to_element(element).perform()
    return element


def post_count_validator(arg):
    try:
        i = int(arg)
    except ValueError:
        raise argparse.ArgumentTypeError("The argument must be an integer")
    if i < 0:
        raise argparse.ArgumentTypeError(f"The argument must be > {0}")
    return i


def logmode_validator(arg):
    if arg in ['w', 'a']:
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


def init_logger(logmode):
    format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(filename='app.log',
                        format=format,
                        level=logging.DEBUG,
                        filemode=logmode)


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


def save(parsed_posts):
    with open(f'{datetime.today().strftime("reddit-%Y%m%d%H%M")}.txt', "w") as file:
        file.writelines([';'.join(parsed_post.values()) + '\n' for parsed_post in parsed_posts])
        logging.info(f'Successful saved to {file.name}')


def parse_post(driver, url, parsed_posts):
    logging.info(f'Url of post: {url}')
    parsed_post = {}
    parsed_post['unique_id'] = str(uuid.uuid1())
    parsed_post['url'] = url
    with open_tab(driver, url):
        get_post_info(driver, parsed_post)
        if get_user_info(driver, parsed_post):
            parsed_posts.append(parsed_post)
            logging.info(f'Successfully parse: {len(parsed_posts)}')


def parse(driver, parsed_posts, count):
    logging.info(f'Parse is starting with count: {count}')
    driver.get('https://www.reddit.com/top/?t=month')
    index = 0
    while len(parsed_posts) < count:
        links = driver.find_elements_by_css_selector(CSS_SELECTORS['POST_LINK'])
        links = links[index:len(links)]
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        for link in links:
            parse_post(driver, link.get_attribute('href'), parsed_posts)
            index += 1
            if (len(parsed_posts)) == count:
                break
    logging.info(f'{count} posts successfully processed')


def get_post_date(driver):
    post_date = get_element_text(driver, CSS_SELECTORS['POST_HOVER_DATE'])
    return dateparser.parse(post_date).strftime("%Y-%m-%d")


def get_post_info(driver, parsed_post):
    parsed_post['post_date'] = get_post_date(driver)
    parsed_post['comment_count'] = get_element_text(driver, CSS_SELECTORS['COMMENT_COUNT']).split(' ')[0]
    parsed_post['vote_count'] = get_element_text(driver, CSS_SELECTORS['VOTE_COUNT'])
    parsed_post['category'] = get_element_text(driver, CSS_SELECTORS['CATEGORY']).split('/')[1]


def get_user_info(driver, parsed_post):
    wait = WebDriverWait(driver, 10)
    parsed_post['username'] = get_element_text(driver, CSS_SELECTORS['USER']).split('/')[1]
    user_element = show_element(driver, CSS_SELECTORS['USER'])
    wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, CSS_SELECTORS['USER_CARD'])))
    card_element = driver.find_elements_by_css_selector(CSS_SELECTORS['CARD_KARMA'])
    parsed_post['post_karma'] = card_element[0].get_attribute('innerHTML')
    parsed_post['comment_karma'] = card_element[1].get_attribute('innerHTML')
    user_element.click()
    try:
        logging.info(f'User: {parsed_post["username"]} is valid')
        parsed_post['user_karma'] = get_element_text(driver, CSS_SELECTORS['USER_KARMA'])
        parsed_post['cake_day'] = get_element_text(driver, CSS_SELECTORS['CAKE_DAY'])
        return True
    except TimeoutException:
        logging.info(f'User: {parsed_post["username"]} is not valid')
        return False


if __name__ == '__main__':
    start = datetime.now()
    parser = argparse.ArgumentParser(description='Reddit parser')
    parser.add_argument('--count', required=False, default=100, type=post_count_validator,
                        help='Count of post to parse')
    parser.add_argument('--logmode', required=False, default='a', type=logmode_validator, help='Log mode')
    args = parser.parse_args()
    parsed_posts = []
    init_logger(args.logmode)
    try:
        with open_webdriver() as driver:
            parse(driver, parsed_posts, args.count)
            save(parsed_posts)
            logging.debug(f'The duration of the scraping: {datetime.now() - start}')
    except WebDriverException as e:
        logging.error(e)
