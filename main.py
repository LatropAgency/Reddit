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


def get_vote_count(driver):
    vote_elem = driver.find_element_by_css_selector('div._1E9mcoVn4MYnuBQSVDt1gC')
    return vote_elem.find_element_by_class_name('_1rZYMD_4xY3gRcSS3p8ODO').text


def get_comment_count(driver):
    comment_elem = driver.find_element_by_css_selector('span.FHCV02u6Cp2zYL0fhQPsO')
    return comment_elem.text.split(' ')[0]


def get_category(driver):
    category_elem = driver.find_element_by_css_selector('span._19bCWnxeTjqzBElWZfIlJb')
    return category_elem.get_attribute('innerHTML').split('/')[1]


def show_date_post_elem(driver):
    date_posted_elem = driver.find_element_by_css_selector("a._3jOxDPIQ0KaOWpzvSQo-1s")
    ActionChains(driver).move_to_element(date_posted_elem).perform()


def get_username(driver):
    user_elem = driver.find_element_by_css_selector(
        "a._2tbHP6ZydRpjI44J3syuqC._23wugcdiaj44hdfugIAlnX.oQctV4n0yUb0uiHDdGnmE")
    return user_elem.get_attribute('innerHTML').split('/')[1]


def get_cake_day(driver):
    cake_day = WebDriverWait(driver, 1).until(
        ec.presence_of_element_located((By.CSS_SELECTOR, "span#profile--id-card--highlight-tooltip--cakeday")))
    return cake_day.get_attribute('innerHTML')


def get_user_karma(driver):
    karma = WebDriverWait(driver, 1).until(
        ec.presence_of_element_located((By.CSS_SELECTOR, "span#profile--id-card--highlight-tooltip--karma")))
    return karma.get_attribute('innerHTML')


def get_user_info(driver, parsed_post):
    parsed_post['username'] = get_username(driver)
    user_elem = driver.find_element_by_css_selector(
        "a._2tbHP6ZydRpjI44J3syuqC._23wugcdiaj44hdfugIAlnX.oQctV4n0yUb0uiHDdGnmE")
    ActionChains(driver).move_to_element(user_elem).perform()
    WebDriverWait(driver, 10).until(ec.presence_of_element_located((By.CSS_SELECTOR, "div._m7PpFuKATP9fZF4xKf9R")))
    html = driver.page_source
    soup = BeautifulSoup(html)
    parsed_post['post_karma'], parsed_post['comment_karma'] = (elem.text for elem in
                                                               soup.find_all(class_='_18aX_pAQub_mu1suz4-i8j'))
    user_elem.click()
    try:
        parsed_post['user_karma'] = get_user_karma(driver)
        parsed_post['cake_day'] = get_cake_day(driver)
        return parsed_post
    except TimeoutException:
        return False


@contextmanager
def open_tab(driver, url):
    parent_han = driver.window_handles[0]
    driver.execute_script("window.open('');")
    logging.info('New tab is opened')
    all_han = driver.window_handles
    new_han = [x for x in all_han if x != parent_han][0]
    driver.switch_to.window(new_han)
    driver.get(url)
    try:
        yield
    finally:
        driver.close()
        logging.info('Tab is closed')
        driver.switch_to.window(parent_han)


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
    unique_id = str(uuid.uuid1())
    parsed_post['unique_id'] = unique_id
    parsed_post['url'] = url
    with open_tab(driver, url):
        get_post_info(driver, parsed_post)
        if get_user_info(driver, parsed_post):
            parsed_posts.append(parsed_post)
            print(len(parsed_posts), parsed_post)
    return parsed_posts


def parse(driver, parsed_posts, count):
    driver.get('https://www.reddit.com/top/?t=month')
    index = 0
    while len(parsed_posts) < count:
        links = driver.find_elements_by_css_selector('a._3jOxDPIQ0KaOWpzvSQo-1s')
        print(len(links))
        links = links[index:len(links)]
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        for link in links:
            parse_post(driver, link.get_attribute('href'), parsed_posts)
            index += 1
            if (len(parsed_posts)) == count:
                break
    logging.info(f'{count} posts successfully processed')


def get_post_date(driver):
    date_elem = WebDriverWait(driver, 10).until(
        ec.visibility_of_element_located((By.CSS_SELECTOR, "div._2J_zB4R1FH2EjGMkQjedwc")))
    post_date = date_elem.text.split(' ')[1:4]
    post_date[0] = str(
        dict((month, index) for index, month in enumerate(calendar.month_abbr) if month)[post_date[0]])
    if len(post_date[0]) == 1:
        post_date[0] = f'0{post_date[0]}'
    return post_date


def get_post_info(driver, parsed_post):
    show_date_post_elem(driver)
    post_date = get_post_date(driver)
    parsed_post['post_date'] = f'{post_date[2]}-{post_date[0]}-{post_date[1]}'
    parsed_post['comment_count'] = get_comment_count(driver)
    parsed_post['vote_count'] = get_vote_count(driver)
    parsed_post['category'] = get_category(driver)


if __name__ == '__main__':
    start = datetime.now()
    parsed_posts = []
    init_logger()
    driver = init_driver()
    parse(driver, parsed_posts, 100)
    save(parsed_posts)
    driver.quit()
    logging.info(f'The duration of the scraping: {datetime.now() - start}')
