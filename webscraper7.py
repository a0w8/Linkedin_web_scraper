# This web scraper will scrape all the jobs from the linkedin site according to the keywords you choose.
# It uses almost exclusively selenium to grab all the elements because of the nature of dynamic sites.
# You can choose to use the firefox webdriver or Chrome. Make sure to uncomment and comment accordingly.
# You need to enter your credentials to the linkedin site.
# I should mention that the windows drivers work better than the linux versions. They are less buggy.
# This scraper runs with the browser open for debugging purposes. Like for example if Linkedin asks you to
# identify as a human. You can run it headless.
# There are many repetitions in this code. to avoid stale element the job element is constantly reloaded
# SQLite is being used as the DB.

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException
import traceback
import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import sqlite3
from sqlite3 import Error



def urlToInteger(url):
    words = urlparse(url).path.strip('/').split('/')
    for word in words:
        try:
            float(word)
            return word
        except ValueError:
            pass
    

def createConn(db):
    conn = None
    try:
        conn = sqlite3.connect(db)
    except Error as e:
        print(e)
    return conn


def jobGenerator(browser):
    while True:
        try:
            length = len(WebDriverWait(browser,5).until(EC.visibility_of_all_elements_located((By.XPATH , '//div[@data-job-id]'))))
        except TimeoutException:
            #browser.refresh()
            #time.sleep(1)
            continue
        #some pages contain less than 25 jobs, 21 jobs spotted
        if length >= 21:
            break
        else:
            element = browser.find_element(By.CLASS_NAME, "jobs-search-results-list")
            ActionChains(browser).scroll_from_origin(ScrollOrigin.from_element(element),0,230).perform()
    job = browser.find_element(By.XPATH, '//div[@data-job-id]')
    while True:
        job_id = job.get_attribute('data-job-id')
        yield job
        try:
            job = browser.find_element(By.XPATH, f'//div[@data-job-id={job_id}]')
            job = job.find_element(By.XPATH, './following::div[@data-job-id]')
        except NoSuchElementException:
            break


def pageGenerator(browser):
    counter=1
    page = browser.find_element(By.XPATH, '//button[@aria-label="Page 1"]')
    while True:
        yield page
        try:
            counter+=1
            page = browser.find_element(By.XPATH, f'//button[@aria-label="Page {counter}"]')
        except NoSuchElementException:
            break


def insertToTable(job_id,job_title,company_id,company,location,data,jobs_cursor,jobs_conn):
    sql_inserto_jobs = ''' INSERT INTO jobs(id,title,company_id,location,data_html) 
                            VALUES(?,?,?,?,?) '''
    sql_inserto_companies = ''' INSERT INTO companies(id,name) VALUES (?,?) '''
    try:
        jobs_cursor.execute(sql_inserto_jobs,(job_id,job_title,company_id,location,data))
        if company_id != None:
            jobs_cursor.execute(sql_inserto_companies,(company_id,company))
        jobs_conn.commit()
    except Error as e:
        if "UNIQUE constraint failed:" not in str(e):
            print(e)



#Authentication
#options = webdriver.ChromeOptions()
#options.add_argument("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36")
#browser = webdriver.Chrome(options=options)
#profile = webdriver.FirefoxProfile()
browser = webdriver.Firefox()
browser.get('https://www.linkedin.com')
user_key = browser.find_element(By.ID, 'session_key')
# Add your username
user_key.send_keys('')
passwd_key = browser.find_element(By.ID, 'session_password')
# Add your password
passwd_key.send_keys('')
browser.find_element(By.XPATH, '//button[contains(text(),"Sign in")]').click()
#debug mode in case of a security check/CAPTCHA. need to comment out headless mode
while urlparse(browser.current_url).path != "/feed/":
    continue

jobs_conn = createConn("jobs.db")
jobs_cursor = jobs_conn.cursor()
sql_create_jobs_table = ''' CREATE TABLE IF NOT EXISTS jobs (
                                  id integer PRIMARY KEY,
                                  title text NOT NULL,
                                  company_id integer,
                                  location text NOT NULL,
                                  data_html text NOT NULL,
                                  requirements text) '''
sql_create_companies_table = ''' CREATE TABLE IF NOT EXISTS companies (
                                   id integer PRIMARY KEY,
                                   name text NOT NULL) '''
try:
    jobs_cursor.execute(sql_create_jobs_table) 
    jobs_cursor.execute(sql_create_companies_table)
except Error as e:
    print(e)

keywords=['linux','support','automation','qa']

for keyword in keywords:
    browser.get(f'https://www.linkedin.com/jobs/search/?keywords={keyword}&location=Israel&refresh=true')
    time.sleep(2)
    for page in pageGenerator(browser):
        page_num = int(page.get_attribute('aria-label').split()[1])
        if int(page_num) != 1:
            page.click()
        time.sleep(1)
        job_counter=1
        # instead of iterating over all the jobs elements in a for loop
        # we iterate one by one in a generated loop. The rational behind is that
        # the linkedin site is dynamic and reloads some elements which make them stale
        for job in jobGenerator(browser):
            job_id = job.get_attribute('data-job-id')
            page_url = browser.current_url
            #each job is checked for stale or no elements, in a loop
            stale_element=1
            while stale_element:
                try:
                    job = browser.find_element(By.XPATH, f'//div[@data-job-id={job_id}]')
                    job.click()

                    #job_print = job.get_attribute('outerHTML')
                    #print(job_print)
                    try:
                        WebDriverWait(browser,3).until(EC.presence_of_element_located((By.XPATH , '//article//span')))
                        WebDriverWait(browser,3).until(EC.presence_of_element_located((By.XPATH , '//a/h2')))
                    except TimeoutException:
                        job = browser.find_element(By.XPATH, f'//div[@data-job-id={job_id}]')
                        if job_counter==1:
                            next_job = job.find_element(By.XPATH, './following::div[@data-job-id]')
                            next_job.click()
                        else:
                            previous_job = job.find_element(By.XPATH, './preceding::div[@data-job-id]')
                            previous_job.click()
                        job.click()
                    data = str(browser.find_element(By.XPATH, '//article//span').get_attribute('outerHTML'))
                    print(data)
                    job_title = browser.find_element(By.XPATH, '//a/h2').text
                    location = job.find_element(By.TAG_NAME, 'li').text
                    #some jobs are missing the company element altogether
                    try:
                        company_elem = job.find_element(By.XPATH, './/a[contains(@href,"/company/")]')
                        company_id_url = company_elem.get_attribute('href')
                        company_id = urlToInteger(company_id_url)
                        company = company_elem.text
                    except NoSuchElementException:
                        company_id = None
                        company = None
                    stale_element = 0
                except (NoSuchElementException,StaleElementReferenceException):
                    print(traceback.format_exc(),end='<br>')
                    # this part is for debugging in case the browser opens a link accidentally 
                    if urlparse(browser.current_url).path != '/jobs/search/':
                        browser.get(page_url)
                        time.sleep(2)
                        break
                    time.sleep(1)
            job_counter+=1
            insertToTable(job_id,job_title,company_id,company,location,data,jobs_cursor,jobs_conn)
            element = browser.find_element(By.CLASS_NAME, "jobs-search-results-list")
            ActionChains(browser).scroll_from_origin(ScrollOrigin.from_element(element),0,130).perform()


jobs_conn.close


#results = soup.find('div', class_ = 'jobs-search-results-list')
#jobs = results.find_all('li', attrs={'data-occludable-job-id'})

