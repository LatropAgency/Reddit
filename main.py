from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

import uuid

import calendar
from datetime import datetime


def init_driver():
    driver = webdriver.Chrome()
    driver.maximize_window()
    return driver


def save(parsed_posts):
    with open(f'{datetime.today().strftime("reddit-%Y%m%d%H%M")}.txt', "w") as file:
        file.writelines([';'.join(parsed_post.values()) + '\n' for parsed_post in parsed_posts])


def parse_post(driver, url, parsed_posts):
    parsed_post = {}
    unique_id = str(uuid.uuid1())
    parsed_post['unique_id'] = unique_id
    parsed_post['url'] = url
    parent_han = driver.window_handles[0]
    driver.execute_script("window.open('');")
    all_han = driver.window_handles
    new_han = [x for x in all_han if x != parent_han][0]
    driver.switch_to.window(new_han)
    if get_posts_info(driver, parsed_post):
        parsed_posts.append(parsed_post)
        print(len(parsed_posts), parsed_post)
    driver.close()
    driver.switch_to.window(parent_han)
    return parsed_posts


def parse(driver, parsed_posts):
    driver.get('https://www.reddit.com/top/?t=month')
    index = 0
    while len(parsed_posts) < 100:
        links = driver.find_elements_by_css_selector('a._3jOxDPIQ0KaOWpzvSQo-1s')
        print(len(links))
        links = links[index:len(links)]
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        for link in links:
            parse_post(driver, link.get_attribute('href'), parsed_posts)
            index += 1
            if (len(parsed_posts)) == 100:
                break


def get_posts_info(driver, parsed_post):
    driver.get(parsed_post['url'])
    wait = WebDriverWait(driver, 10)
    user_elem = driver.find_element_by_css_selector(
        "a._2tbHP6ZydRpjI44J3syuqC._23wugcdiaj44hdfugIAlnX.oQctV4n0yUb0uiHDdGnmE")
    parsed_post['username'] = user_elem.text[2:len(user_elem.text)]
    date_posted_elem = driver.find_element_by_css_selector("a._3jOxDPIQ0KaOWpzvSQo-1s")
    ActionChains(driver).move_to_element(date_posted_elem).perform()
    date_elem = wait.until(
        ec.visibility_of_element_located((By.CSS_SELECTOR, "div._2J_zB4R1FH2EjGMkQjedwc")))
    post_date = date_elem.text.split(' ')[1:4]
    post_date[0] = str(
        dict((month, index) for index, month in enumerate(calendar.month_abbr) if month)[post_date[0]])
    if len(post_date[0]) == 1:
        post_date[0] = f'0{post_date[0]}'
    parsed_post['post_date'] = f'{post_date[2]}-{post_date[0]}-{post_date[1]}'
    comment_elem = driver.find_element_by_css_selector('span.FHCV02u6Cp2zYL0fhQPsO')
    parsed_post['comment_count'] = comment_elem.text.split(' ')[0]
    vote_elem = driver.find_element_by_css_selector('div._1E9mcoVn4MYnuBQSVDt1gC')
    parsed_post['vote_count'] = vote_elem.find_element_by_class_name('_1rZYMD_4xY3gRcSS3p8ODO').text
    parsed_post['category'] = driver.find_element_by_css_selector('span._19bCWnxeTjqzBElWZfIlJb').text
    ActionChains(driver).move_to_element(user_elem).perform()
    wait.until(ec.visibility_of_element_located((By.CSS_SELECTOR, "div._m7PpFuKATP9fZF4xKf9R")))
    html = driver.page_source
    soup = BeautifulSoup(html)
    post_karma, comment_karma = (elem.text for elem in soup.find_all(class_='_18aX_pAQub_mu1suz4-i8j'))
    parsed_post['post_karma'] = post_karma
    parsed_post['comment_karma'] = comment_karma
    user_elem.click()
    try:
        wait.until(
            ec.visibility_of_element_located((By.CSS_SELECTOR, "span#profile--id-card--highlight-tooltip--karma")))
        karma = driver.find_element_by_id('profile--id-card--highlight-tooltip--karma')
        parsed_post['user_karma'] = karma.text
        cake_day = driver.find_element_by_id('profile--id-card--highlight-tooltip--cakeday')
        parsed_post['cake_day'] = cake_day.text
        return parsed_post
    except TimeoutException:
        pass


if __name__ == '__main__':
    parsed_posts = []
    driver = init_driver()
    parse(driver, parsed_posts)
    save(parsed_posts)
    driver.quit()
