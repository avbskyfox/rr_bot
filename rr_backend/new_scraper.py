from selenium import webdriver
from selenium.webdriver.common.keys import Keys

driver = webdriver.PhantomJS()


REQUEST_URL = 'https://rosreestr.gov.ru/wps/portal/online_request'


def main():
    driver.get(REQUEST_URL)

if __name__ == '__main__':
    main()