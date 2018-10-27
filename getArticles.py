import re
import psycopg2
import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

startTime = datetime.datetime.now()
# startTime = startTime - datetime.timedelta(2)
options = Options()
options.add_argument("--headless")
date_for_url = str(startTime.day) + '.' + str(startTime.month) + '.' + str(startTime.year)
main_url = 'https://www.delfi.lt/archive/latest.php?query=&tod=' + date_for_url + '&fromd=' + date_for_url + '&channel=1&category=0'

driver = webdriver.Firefox(firefox_options=options)

print("-- Firefox Headless Browser Invoked")

driver.get(main_url)
html = driver.execute_script("return document.documentElement.outerHTML")
sel_soup = BeautifulSoup(html, 'html.parser')

try:
    headlines = sel_soup.find_all('div', {'class': 'headline'})
    links = []
    for headline in headlines:
        headline_link = headline.a['href']
        headline_id = headline_link[headline_link.find('id=') + 3:]
        links.append({'link': headline_link, 'id': headline_id})
except:
    print ('Error occurred while scraping for urls!')
print ('-- Found all recent articles')
print (len(links))
conn = psycopg2.connect('dbname=vvtest user=postgres password=piskmane908 host=localhost')
try:
    counter = 0;
    for url in links:
        with conn.cursor() as cur:
            counter += 1
            print(counter);
            cur.execute('SELECT COUNT(*) from articles WHERE source_url = %s;', (url['link'],))
            duplicateCount = cur.fetchone()[0]
            print ('---- Checking for duplicates')
            if (duplicateCount > 0):
                print ('-- Duplicate found, skipping article')
                continue
            print ('--- Retrieving new article')
            driver.get(url['link'])
            html = driver.execute_script("return document.documentElement.outerHTML")
            sel_soup = BeautifulSoup(html, 'html.parser')
            try:
                articleTitle = (sel_soup.find('h1', {'itemprop': 'headline'}).text.strip())
            except:
                articleTitle = 'NULL'

            try:
                articlePostDate = sel_soup.find('meta', {'itemprop': 'datePublished'})['content'].strip()
            except:
                articlePostDate = 'NULL'

            try:
                articleAuthor = (sel_soup.find('div', {'itemprop': 'author'}).string)
            except:
                articleAuthor = 'NULL'

            try:
                articleAuthorTitle = (sel_soup.find('div', {'class': 'delfi-author-title'}).text.strip())
            except:
                articleAuthorTitle = 'NULL'

            try:
                sel_soup.find('div', {'class': 'related-box'}).decompose()
            except:
                pass
            try:
                articleImageLink = sel_soup.find('div', {'class': 'image-article'}).find('a')['href'].strip()
            except:
                pass
            try:
                for imgArticle in (sel_soup.find_all('div', {'class': 'image-article'})):
                    sel_soup.find('div', {'class': 'image-article'}).decompose()
            except:
                print('nesuveike')
                pass

            for script in sel_soup('script'):
                script.decompose()
            try:
                articleText = (sel_soup.find('div', {'itemprop': 'articleBody'}).contents)

                parsedText = []
                for item in articleText:
                    try:
                        parsedText.append(item.text.strip())
                    except:
                        pass
                parsedText = ' '.join(parsedText)

                cur.execute('SELECT lastname_root, id FROM politicians;')
                politician_data = cur.fetchall()
                capitalized_words = re.findall('([A-Z][a-z]+)', parsedText)

                found = []
                for name in politician_data:
                    for word in capitalized_words:
                        if name[0] in word:
                            found.append(name)
                found = list(set(found))
                now = str(datetime.datetime.now().isoformat())
                if articlePostDate == 'NULL' or articlePostDate == '':
                    articlePostDate = now
                if len(found) > 0:
                    query = """INSERT INTO
                    articles (source, title, image_link, about_politicians, article_body, author, author_title, source_date, source_url, "createdAt", "updatedAt")
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""
                    cur.execute(
                    query,
                    (
                    'Delfi',
                    articleTitle,
                    articleImageLink,
                    True,
                    parsedText,
                    articleAuthor,
                    articleAuthorTitle,
                    articlePostDate,
                    url['link'],
                    now,
                    now
                    )
                    )
                    cur.execute("SELECT id FROM articles WHERE source_url = %s;", (url['link'],))

                    article_id = cur.fetchone()
                    for item in found:
                        now = str(datetime.datetime.now().isoformat())
                        cur.execute("""INSERT INTO polit_in_articles ("politicianId", "articleId", "createdAt", "updatedAt")
                        VALUES (%s, %s, %s, %s);""", (item[1], str(article_id[0]), now, now))
                    print ('- Connected with politician ' + str(item[1]))
                else:
                    query = """INSERT INTO
                    articles (source, title, image_link, about_politicians, author, author_title, source_date, source_url, "createdAt", "updatedAt")
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""
                    cur.execute(
                    query,
                    (
                    'Delfi',
                    articleTitle,
                    articleImageLink,
                    False,
                    articleAuthor,
                    articleAuthorTitle,
                    articlePostDate,
                    url['link'],
                    now,
                    now
                    )
                    )
                conn.commit()
                print ('-- Article added')
            except Exception as e:
                print ('Error while inserting into database')
                print (e)

except Exception as e:
    print ('Error:')
    print (e)

conn.close()

driver.quit()

print ('Script run time')
print (datetime.datetime.now() - startTime)
