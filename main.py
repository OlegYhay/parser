import csv
import re
import zipfile

from bs4 import BeautifulSoup
import configparser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from proxy_settings import manifest_json, background_js

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8-sig')
user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
LOGIN_PROXY = config.get('proxy', 'user')
PASSWORD_PROXY = config.get('proxy', 'password')

ADDRESS = "проспект Альберта Камалеева, 32Б, Казань, Республика Татарстан"

SHOPS = [
    "metro",
    "lenta",
    "auchan",
]

CATEGORIES = [
    "ovoshchi-frukti-orekhi",
    "sladosti_new",
    "bakaleya",
]


def getchromedriver(use_proxy=False):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    if use_proxy:
        plugin_file = 'proxy_auth_plugin.zip'

        with zipfile.ZipFile(plugin_file, 'w') as zp:
            zp.writestr('manifest.json', manifest_json)
            zp.writestr('background.js', background_js)

        chrome_options.add_extension(plugin_file)
        chrome_options.add_argument(f'--user-agent={user_agent}')
        driver = webdriver.Chrome(options=chrome_options)
    return driver


def main():
    # Если прокси не работает, передайте False для его отключения
    driver = getchromedriver(True)
    driver.get('https://sbermarket.ru/')

    print('Установка адреса....')

    # Проверка двух вспылвающих окон(ввод телефона и рекламное предложение)
    try:
        elem = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME,
                                                                               "ModalWrapper_root__54KLk")))
        button_close_enter_number = elem.find_element(By.CLASS_NAME, 'Button_root__WicTg')
        button_close_enter_number.click()
    except:
        try:
            elem = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME,
                                                                                   "Modal_closeButton__mxGEQ")))
            elem.click()
        except:
            pass

    # сбер запрашивал капчу
    driver.get_screenshot_as_file("screenshot.png")

    # Установка адреса
    input_address = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CLASS_NAME, "Address_input__D7sP_")))
    input_address.send_keys(ADDRESS)

    list_address = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CLASS_NAME, "styles_dropdown__l_lU6")))
    WebDriverWait(list_address, 5).until(EC.element_to_be_clickable((By.XPATH,
                                                                     "/html/body/div[1]/div/div[1]/div/div[1]/div/div[1]/div[1]/div[2]/div[1]/div/div/div[2]/div/div[1]/div"))).click()
    print('Адрес установлен!')
    # получение товара для магазинов указанных в shops
    for shop in SHOPS:
        for category in CATEGORIES:
            print(f'Формирование файла товара магазина {shop}, категория {category} ')
            get_shop_gods(driver, shop, category)


def get_shop_gods(driver, shop, category):
    # Переход в раздел магазина и категории
    driver.get(f"https://sbermarket.ru/{shop}/c/{category}/")

    wait = WebDriverWait(driver, 30)
    # Открытия всех товаров данного раздела
    element = wait.until(EC.element_to_be_clickable((By.XPATH,
                                                     "/html/body/div[1]/div/div[1]/div[3]/div[2]/div/main/section/div/div/div/div/ul/li[1]/section/div[1]/a[2]/div")))
    element.click()
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME,
                                                                    "Products_root__n55WH")))
    current_url = driver.current_url

    # Переход по 3 страницам открытой категории и сохранение данных
    with open(f"result_files/{shop}_{category}.csv", "w", newline="") as file:
        for page in range(1, 4):
            driver.get(f'{current_url}&page={page}')
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            object_goods = soup.find_all('div', class_='ProductCard_root__K6IZK')
            writer = csv.writer(file, delimiter=';')
            write_goods(object_goods, writer, category)

    print('Конец.')


def write_goods(object_goods, writer, category):
    for row in object_goods:
        row_data = []
        row_data.append(ADDRESS)
        row_data.append(category)
        link = row.find('a', class_='ProductCardLink_root__69qxV')
        row_data.append(link['href'])

        name = row.find('h3', class_='ProductCard_title__iNsaD')
        row_data.append(name.text.strip())

        img_small_link = row.find('img', class_='ProductCard_image__3jwTC')
        row_data.append(img_small_link['src'])

        img_big_link = row.find('source')
        img_big_link = str(img_big_link['srcset']).split(',')
        row_data.append(img_big_link[1])

        price_div = row.find('div', class_='ProductCardPrice_price__Kv7Q7')
        price = re.findall("\d+[,]\d*", price_div.text.strip())
        row_data.append(price[0])

        price_discount_div = row.find('div', class_='ProductCardPrice_originalPrice__z36Di')
        if price_discount_div != None:
            price = re.findall(r'\d+[,]\d*', price_discount_div.text.strip())
            row_data.append(price[0])
        else:
            row_data.append('-')

        writer.writerow(row_data)


if __name__ == '__main__':
    main()
