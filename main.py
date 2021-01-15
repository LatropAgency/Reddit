from bs4 import BeautifulSoup
from selenium import webdriver
import uuid
from datetime import datetime


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
    lines = []
    for post in posts:
        unique_id = str(uuid.uuid1())
        post_url = post.find('a', class_='_3jOxDPIQ0KaOWpzvSQo-1s')['href']
        lines.append(';'.join([unique_id, post_url]) + '\n')
    with open(f'{datetime.today().strftime("%Y%m%d%H%M")}.txt', "w") as file:
        file.writelines(lines)
    driver.quit()
