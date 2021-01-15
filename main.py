from bs4 import BeautifulSoup
from selenium import webdriver
import uuid
from datetime import datetime


def save(parsed_posts):
    lines = []
    for parsed_post in parsed_posts:
        lines.append(';'.join(parsed_post.values()) + '\n')
    with open(f'{datetime.today().strftime("%Y%m%d%H%M")}.txt', "w") as file:
        file.writelines(lines)


def parse_posts(posts):
    parsed_posts = []
    for post in posts:
        parsed_post = {}
        unique_id = str(uuid.uuid1())
        parsed_post['unique_id'] = unique_id
        parsed_post['url'] = post.find('a', class_='_3jOxDPIQ0KaOWpzvSQo-1s')['href']
        parsed_posts.append(parsed_post)
    return parsed_posts


def init_driver():
    return webdriver.Chrome()


def get_posts(driver):
    driver.get('https://www.reddit.com/top/?t=month')
    html = driver.page_source
    soup = BeautifulSoup(html)
    # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    return soup.find_all('div', class_='Post')


if __name__ == '__main__':
    driver = init_driver()
    posts = get_posts(driver)
    parsed_posts = parse_posts(posts)
    save(parsed_posts)
    driver.quit()
