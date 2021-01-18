import logging
from contextlib import contextmanager

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.chrome.options import Options

import uuid

import calendar
from datetime import datetime

CONSTANTS = {
    'VOTE_COUNT_CSS_SELECTOR': '._1rZYMD_4xY3gRcSS3p8ODO',
    'COMMENT_COUNT_CSS_SELECTOR': 'span.FHCV02u6Cp2zYL0fhQPsO',
    'CAKE_DAY_CSS_SELECTOR': 'span#profile--id-card--highlight-tooltip--cakeday',
    'USER_KARMA_CSS_SELECTOR': 'span#profile--id-card--highlight-tooltip--karma',
    'CATEGORY_CSS_SELECTOR': 'span._19bCWnxeTjqzBElWZfIlJb',
    'POST_DATE_CSS_SELECTOR': 'div._2J_zB4R1FH2EjGMkQjedwc',
    'POST_HOVER_DATE_CSS_SELECTOR': 'a._3jOxDPIQ0KaOWpzvSQo-1s',
    'POST_LINK_CSS_SELECTOR': 'a._3jOxDPIQ0KaOWpzvSQo-1s',
    'USER_CSS_SELECTOR': 'a._2tbHP6ZydRpjI44J3syuqC._23wugcdiaj44hdfugIAlnX.oQctV4n0yUb0uiHDdGnmE',
    'USER_CARD_CSS_SELECTOR': 'div._m7PpFuKATP9fZF4xKf9R',
    'CARD_KARMA_CSS_SELECTOR': 'div._18aX_pAQub_mu1suz4-i8j',
}


def get_element_text(driver, css_selector):
    return WebDriverWait(driver, 10) \
        .until(ec.presence_of_element_located((By.CSS_SELECTOR, css_selector))) \
        .get_attribute('innerHTML')


def show_element(driver, css_selector):
    element = driver.find_element_by_css_selector(css_selector)
    ActionChains(driver).move_to_element(element).perform()
    return element


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
    logging.info('New tab is opened')
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


def init_logger():
    logging.basicConfig(filename='app.log', format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)


def init_driver():
    options = Options()
    prefs = {'profile.default_content_setting_values': {'images': 2}}
    options.add_experimental_option('prefs', prefs)
    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    logging.info('WebDriver is initialized')
    return driver


def save(parsed_posts):
    with open(f'{datetime.today().strftime("reddit-%Y%m%d%H%M")}.txt', "w") as file:
        file.writelines([';'.join(parsed_post.values()) + '\n' for parsed_post in parsed_posts])
    logging.info('Successful saving')


def parse_post(driver, url, parsed_posts):
    parsed_post = {}
    parsed_post['unique_id'] = str(uuid.uuid1())
    parsed_post['url'] = url
    with open_tab(driver, url):
        get_post_info(driver, parsed_post)
        if get_user_info(driver, parsed_post):
            parsed_posts.append(parsed_post)
    return parsed_posts


def parse(driver, parsed_posts, count):
    driver.get('https://www.reddit.com/top/?t=month')
    index = 0
    while len(parsed_posts) < count:
        links = driver.find_elements_by_css_selector(CONSTANTS['POST_LINK_CSS_SELECTOR'])
        links = links[index:len(links)]
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        for link in links:
            parse_post(driver, link.get_attribute('href'), parsed_posts)
            index += 1
            if (len(parsed_posts)) == count:
                break
    logging.info(f'{count} posts successfully processed')


def get_post_date(driver):
    show_element(driver, CONSTANTS['POST_HOVER_DATE_CSS_SELECTOR'])
    post_date = get_element_text(driver, CONSTANTS['POST_DATE_CSS_SELECTOR']).split(' ')[1:4]
    post_date[0] = str(
        dict((month, index) for index, month in enumerate(calendar.month_abbr) if month)[post_date[0]])
    if len(post_date[0]) == 1:
        post_date[0] = f'0{post_date[0]}'
    return f'{post_date[2]}-{post_date[0]}-{post_date[1]}'


def get_post_info(driver, parsed_post):
    parsed_post['post_date'] = get_post_date(driver)
    parsed_post['comment_count'] = get_element_text(driver, CONSTANTS['COMMENT_COUNT_CSS_SELECTOR']).split(' ')[0]
    parsed_post['vote_count'] = get_element_text(driver, CONSTANTS['VOTE_COUNT_CSS_SELECTOR'])
    parsed_post['category'] = get_element_text(driver, CONSTANTS['CATEGORY_CSS_SELECTOR']).split('/')[1]


def get_user_info(driver, parsed_post):
    wait = WebDriverWait(driver, 10)
    parsed_post['username'] = get_element_text(driver, CONSTANTS['USER_CSS_SELECTOR']).split('/')[1]
    user_element = show_element(driver, CONSTANTS['USER_CSS_SELECTOR'])
    wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, CONSTANTS['USER_CARD_CSS_SELECTOR'])))
    card_element = driver.find_elements_by_css_selector(CONSTANTS['CARD_KARMA_CSS_SELECTOR'])
    parsed_post['post_karma'] = card_element[0].get_attribute('innerHTML')
    parsed_post['comment_karma'] = card_element[1].get_attribute('innerHTML')
    user_element.click()
    try:
        parsed_post['user_karma'] = get_element_text(driver, CONSTANTS['USER_KARMA_CSS_SELECTOR'])
        parsed_post['cake_day'] = get_element_text(driver, CONSTANTS['CAKE_DAY_CSS_SELECTOR'])
        return True
    except TimeoutException:
        return False


if __name__ == '__main__':
    start = datetime.now()
    parsed_posts = []
    init_logger()
    with open_webdriver() as driver:
        parse(driver, parsed_posts, 100)
        save(parsed_posts)
    logging.info(f'The duration of the scraping: {datetime.now() - start}')
