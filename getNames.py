import re
import psycopg2
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

options = Options()
options.add_argument("--headless")

url = 'http://www.lrs.lt/sip/portal.show?p_r=8801&p_k=1&filtertype=1'

driver = webdriver.Firefox(firefox_options=options)
driver.get(url)
html = driver.execute_script("return document.documentElement.outerHTML")

sel_soup = BeautifulSoup(html, 'html.parser')
endings = ['aitė', 'ytė', 'utė', 'ūtė', 'iūtė', 'ė', 'ienė', 'us', 'ius', 'jus', 'uvienė', 'iuvienė', 'ienė', 'is', 'as', 'a', 'ys']
conn = psycopg2.connect('dbname=vvtest user=postgres password=piskmane908 host=localhost')
iterator = 1
with conn.cursor() as cur:
    for smn in sel_soup.find_all('div', {'class': 'list-member'}):
        print ('Getting name')
        last_name = 'NULL'
        first_name = 'NULL'
        last_name_root = 'NULL'
        postion = 'NULL'
        try:
            last_name = smn.find('span', {'class': 'smn-pavarde'}).text.strip()
            first_name = smn.find('a', {'class': 'smn-name'}).text.strip()[:-len(last_name)]
            position = smn.find('div', {'class': 'smn-pareigos'}).text.strip()
            last_name_root = last_name
            for end in endings:
                if last_name[-len(end):] == end:
                    last_name_root = last_name[:-len(end)]
                    break

            now = str(datetime.now().isoformat())

            cur.execute("""INSERT INTO
            politicians (firstname, lastname, lastname_root, position, "createdAt", "updatedAt")
            VALUES (%s, %s, %s, %s, %s, %s);""", (first_name, last_name, last_name_root, position, now, now))
            conn.commit()
            print ('Nr.' + str(iterator))
            print ('Name added')
            iterator += 1
        except Exception as e:
            print ('Error:')
            print (e)
conn.cancel()
driver.quit()
