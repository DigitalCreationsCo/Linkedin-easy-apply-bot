from __future__ import annotations
import time, random, os, csv, platform
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import pyautogui

from urllib.request import urlopen
from webdriver_manager.chrome import ChromeDriverManager
import re
import yaml
from datetime import datetime, timedelta

log = logging.getLogger(__name__)
driver = webdriver.Chrome(ChromeDriverManager().install())

def setupLogger() -> None:
    dt: str = datetime.strftime(datetime.now(), "%m_%d_%y %H_%M_%S ")

    if not os.path.isdir('./logs'):
        os.mkdir('./logs')

    # TODO need to check if there is a log dir available or not
    logging.basicConfig(filename=('./logs/' + str(dt) + 'applyJobs.log'), filemode='w',
                        format='%(asctime)s::%(name)s::%(levelname)s::%(message)s', datefmt='./logs/%d-%b-%y %H:%M:%S')
    log.setLevel(logging.DEBUG)
    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.DEBUG)
    c_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S')
    c_handler.setFormatter(c_format)
    log.addHandler(c_handler)

class EasyApplyBot:
    setupLogger()
    # MAX_SEARCH_TIME is 10 hours by default, feel free to modify it
    MAX_SEARCH_TIME = 10 * 60 * 60
    MAX_SIGN_IN_ATTEMPTS = 3
    username: str
    password: str

    def __init__(self,
                 username,
                 password,
                 first_name,
                 last_name,
                 salary,
                 experience,
                 address,
                 city,
                 state,
                 zipcode,
                 country,
                 phone_number,
                 uploads={},
                 filename='output.csv',
                 blacklist=[],
                 blackListTitles=[]) -> None:

        log.info("Welcome to Easy Apply Bot")
        dirpath: str = os.getcwd()
        log.info("current directory is : " + dirpath)

        self.username = username
        self.password = password
        self.first_name = first_name
        self.last_name = last_name
        self.salary = salary
        self.experience = experience
        self.address = address
        self.city = city
        self.state = state
        self.zipcode = zipcode
        self.country = country
        self.phone_number = phone_number

        self.uploads = uploads
        past_ids: list | None = self.get_appliedIDs(filename)
        self.appliedJobIDs: list = past_ids if past_ids != None else []
        self.filename: str = filename
        self.options = self.browser_options()
        self.browser = driver
        self.wait = WebDriverWait(self.browser, 30)
        self.blacklist = blacklist
        self.blackListTitles = blackListTitles
        self.start_linkedin(username, password)

    def get_appliedIDs(self, filename) -> list | None:
        try:
            df = pd.read_csv(filename,
                             header=0,
                             names=['timestamp', 'jobID', 'job', 'company', 'attempted', 'result'],
                             lineterminator='\n',
                             encoding='utf-8')

            df['timestamp'] = pd.to_datetime(df['timestamp'], format="%Y-%m-%d %H:%M:%S")
            df = df[df['timestamp'] > (datetime.now() - timedelta(days=2))]
            jobIDs: list = list(df.jobID)
            log.info(f"{len(jobIDs)} jobIDs found")
            return jobIDs
        except Exception as e:
            log.info(str(e) + "   jobIDs could not be loaded from CSV {}".format(filename))
            return None

    def browser_options(self):
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument('--no-sandbox')
        options.add_argument("--disable-extensions")

        # Disable webdriver flags or you will be easily detectable
        options.add_argument("--disable-blink-features")
        options.add_argument("--disable-blink-features=AutomationControlled")
        return options

    def start_linkedin(self, username, password, attempt=1) -> None:

        if attempt > self.MAX_SIGN_IN_ATTEMPTS:
            print("Max login attempts reached. Exiting.")
            return
    
        log.info("Logging in.....Please wait :)  ")
        self.browser.get("https://www.linkedin.com/login?trk=guest_homepage-basic_nav-header-signin")
        try:
            user_field = self.browser.find_element("id","username")
            pw_field = self.browser.find_element("id","password")
            login_button = self.browser.find_element(By.XPATH,
                        '//*[@id="organic-div"]/form/div[3]/button')
            user_field.send_keys(username)
            user_field.send_keys(Keys.TAB)
            time.sleep(2)
            pw_field.send_keys(password)
            time.sleep(2)
            login_button.click()
            time.sleep(3)

             # Check if login was successful, if not, retry
            if "feed" not in self.browser.current_url:  # Assuming "feed" is in the URL after successful login

                # Pause for manual security check
                print("Please complete the security check manually and press Enter to continue...")
                input("Press Enter to continue...")

                time.sleep(3)
                # After completing the security check manually, the script will resume here
                # Verify if the login was successful
                if "feed" in self.browser.current_url:
                    print("Login successful.")
                else:
                    print("Login failed. Please try again.")
                    self.start_linkedin(self.username, self.password, attempt + 1)
            else:
                print("Login successful.")
        except TimeoutException:
            log.info("TimeoutException! Username/password field or login button not found")

    def fill_data(self) -> None:
        self.browser.set_window_size(1, 1)
        self.browser.set_window_position(2000, 2000)

    def start_apply(self, positions, locations) -> None:
        start: float = time.time()
        self.fill_data()

        

        combos: list = []
        while len(combos) < len(positions) * len(locations):
            position = positions[random.randint(0, len(positions) - 1)]
            location = locations[random.randint(0, len(locations) - 1)]
            combo: tuple = (position, location)
            if combo not in combos:
                combos.append(combo)
                log.info(f"Applying to {position}: {location}")
                location = "&location=" + location
                self.applications_loop(position, location)
            if len(combos) > 500:
                break

    def applications_loop(self, position, location):

        count_application = 0
        count_job = 0
        jobs_per_page = 0
        start_time: float = time.time()

        log.info("Looking for jobs.. Please wait..")

        self.browser.set_window_position(1, 1)
        self.browser.maximize_window()
        self.browser, _ = self.next_jobs_page(position, location, jobs_per_page)
        log.info("Looking for jobs.. Please wait..")

        while time.time() - start_time < self.MAX_SEARCH_TIME:
            try:
                log.info(f"{(self.MAX_SEARCH_TIME - (time.time() - start_time)) // 60} minutes left in this search")

                # sleep to make sure everything loads, add random to make us look human.
                randoTime: float = random.uniform(3.5, 4.9)
                log.debug(f"Sleeping for {round(randoTime, 1)}")
                time.sleep(randoTime)
                self.load_page(sleep=1)

                time.sleep(1)

                # get job links, (the following are actually the job card objects)
                links = self.browser.find_elements("xpath",
                    '//div[@data-job-id]'
                )

                if len(links) == 0:
                    log.debug("No links found")
                    break

                IDs: list = []
                
                # children selector is the container of the job cards on the left
                for link in links:
                    children = link.find_elements("xpath",
                        '//ul[@class="scaffold-layout__list-container"]'
                    )
                    for child in children:
                        if child.text not in self.blacklist:
                            temp = link.get_attribute("data-job-id")
                            jobID = temp.split(":")[-1]
                            IDs.append(int(jobID))
                IDs: list = set(IDs)

                # remove already applied jobs
                before: int = len(IDs)
                jobIDs: list = [x for x in IDs if x not in self.appliedJobIDs]
                after: int = len(jobIDs)

                # it assumed that 25 jobs are listed in the results window
                if len(jobIDs) == 0 and len(IDs) > 23:
                    jobs_per_page = jobs_per_page + 25
                    count_job = 0
                    self.avoid_lock()
                    self.browser, jobs_per_page = self.next_jobs_page(position,
                                                                    location,
                                                                    jobs_per_page)
                # loop over IDs to apply
                for i, jobID in enumerate(jobIDs):
                    count_job += 1
                    self.get_job_page(jobID)

                    # get easy apply button
                    button = self.get_easy_apply_button()
                    # word filter to skip positions not wanted

                    if button is not False:
                        if any(word in self.browser.title for word in self.blackListTitles):
                            log.info('skipping this application, a blacklisted keyword was found in the job position')
                            string_easy = "* Contains blacklisted keyword"
                            result = False
                        else:
                            string_easy = "* has Easy Apply Button"
                            log.info("Clicking the EASY apply button")
                            button.click()
                            time.sleep(3)
                            self.fill_out_phone_number()
                            result: bool = self.send_resume()
                            count_application += 1
                    else:
                        log.info("The button does not exist.")
                        string_easy = "* Doesn't have Easy Apply Button"
                        result = False

                    position_number: str = str(count_job + jobs_per_page)
                    log.info(f"\nPosition {position_number}:\n {self.browser.title} \n {string_easy} \n")

                    self.write_to_file(button, jobID, self.browser.title, result)

                    # sleep every 20 applications
                    if count_application != 0 and count_application % 20 == 0:
                        sleepTime: int = random.randint(500, 900)
                        log.info(f"""********count_application: {count_application}************\n\n
                                    Time for a nap - see you in:{int(sleepTime / 60)} min
                                ****************************************\n\n""")
                        time.sleep(sleepTime)

                    # go to new page if all jobs are done
                    if count_job == len(jobIDs):
                        jobs_per_page = jobs_per_page + 25
                        count_job = 0
                        log.info("""****************************************\n\n
                        Going to next jobs page, YEAAAHHH!!
                        ****************************************\n\n""")
                        self.avoid_lock()
                        self.browser, jobs_per_page = self.next_jobs_page(position,
                                                                        location,
                                                                        jobs_per_page)
            except Exception as e:
                print(e)

    def write_to_file(self, button, jobID, browserTitle, result) -> None:
        def re_extract(text, pattern):
            target = re.search(pattern, text)
            if target:
                target = target.group(1)
            return target

        timestamp: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        attempted: bool = False if button == False else True
        job = re_extract(browserTitle.split(' | ')[0], r"\(?\d?\)?\s?(\w.*)")
        company = re_extract(browserTitle.split(' | ')[1], r"(\w.*)")

        toWrite: list = [timestamp, jobID, job, company, attempted, result]
        with open(self.filename, 'a') as f:
            writer = csv.writer(f)
            writer.writerow(toWrite)

    def get_job_page(self, jobID):

        job: str = 'https://www.linkedin.com/jobs/view/' + str(jobID)
        self.browser.get(job)
        self.job_page = self.load_page(sleep=0.5)
        return self.job_page

    def get_easy_apply_button(self):
        try:
            button = self.browser.find_elements(By.XPATH,
                '//button[contains(@class, "jobs-apply-button")]'
            )
            print('buttons found: ', button)
            EasyApplyButton =  button[1] if len(button) > 1 else button[0] if len(button) > 0 else False
            # EasyApplyButton = button[0]
            
        except Exception as e: 
            print("Exception:",e)
            EasyApplyButton = False

        return EasyApplyButton

    def fill_out_phone_number(self):
        def is_present(button_locator) -> bool:
            return len(self.browser.find_elements(button_locator[0],
                                                  button_locator[1])) > 0
        next_locater = (By.CSS_SELECTOR,
                        "button[aria-label='Continue to next step']")

        input_field = self.browser.find_element(By.CSS_SELECTOR, "input.artdeco-text-input--input[type='text']")

        if input_field:
            input_field.clear()
            input_field.send_keys(self.phone_number)
            time.sleep(random.uniform(4.5, 6.5))
        


            next_locater = (By.CSS_SELECTOR,
                            "button[aria-label='Continue to next step']")
            error_locator = (By.CSS_SELECTOR,
                             "p[data-test-form-element-error-message='true']")

            # Click Next or submit button if possible
            button: None = None
            if is_present(next_locater):
                button: None = self.wait.until(EC.element_to_be_clickable(next_locater))

            if is_present(error_locator):
                for element in self.browser.find_elements(error_locator[0],
                                                            error_locator[1]):
                    text = element.text
                    if "Please enter a valid answer" in text:
                        button = None
                        break
            if button:
                button.click()
                time.sleep(random.uniform(1.5, 2.5))
                # if i in (3, 4):
                #     submitted = True
                # if i != 2:
                #     break



        else:
            log.debug(f"Could not find phone number field")
                


    def send_resume(self) -> bool:
        def is_present(button_locator) -> bool:
            return len(self.browser.find_elements(button_locator[0],
                                                  button_locator[1])) > 0

        try:
            time.sleep(random.uniform(1.5, 2.5))
            
            questions_heading_locator = (By.XPATH, "//form//h3[contains(text(), 'Additional Questions')]")
            
            work_authorization_heading_locator = (By.XPATH, "//form//h3[contains(text(), 'Work authorization')]")
            
            next_locater = (By.CSS_SELECTOR,
                            "button[aria-label='Continue to next step']")
            review_locater = (By.CSS_SELECTOR,
                              "button[aria-label='Review your application']")
            submit_locater = (By.CSS_SELECTOR,
                              "button[aria-label='Submit application']")
            submit_application_locator = (By.CSS_SELECTOR,
                                          "button[aria-label='Submit application']")
            error_locator = (By.CSS_SELECTOR,
                             "p[data-test-form-element-error-message='true']")
            upload_locator = upload_locator = (By.XPATH, "//*[contains(@aria-label, 'DOC, DOCX, PDF formats are supported. Max file size is (2 MB)')]")
            follow_locator = (By.CSS_SELECTOR, "label[for='follow-company-checkbox']")

            submitted = False
            while True:
                log.info(f"upload locator is present: {is_present(upload_locator)}")

                if is_present(upload_locator):

                    input_buttons = self.browser.find_elements(upload_locator[0],
                                                               upload_locator[1])
                    
                    log.info(f"input_buttons: {input_buttons}")
                    for input_button in input_buttons:
                        descendant_input = input_button.find_element(By.XPATH, "../..//input")
                        log.info(f"descendant_input: {descendant_input}")
                        for key in self.uploads.keys():
                            if key.lower() in descendant_input.get_attribute('id').lower():
                                descendant_input.send_keys(self.uploads[key])

                    time.sleep(random.uniform(4.5, 6.5))

                # Click Next or submit button if possible
                button: None = None
                buttons: list = [next_locater, review_locater, follow_locator,
                           submit_locater, submit_application_locator]
                for i, button_locator in enumerate(buttons):

                    self.answer_questions()
                
                    if is_present(button_locator):
                        button: None = self.wait.until(EC.element_to_be_clickable(button_locator))

                    if is_present(error_locator):
                        for element in self.browser.find_elements(error_locator[0],
                                                                  error_locator[1]):
                            text = element.text
                            if "Please enter a valid answer" in text:
                                button = None
                                break
                    if button:
                        
                        print(f"button found: {buttons[i]}")

                        button.click()
                        print(f"Clicked button {buttons[i]}")

                        time.sleep(random.uniform(1.5, 2.5))
                        if i in (3, 4):
                            submitted = True
                        if i != 2:
                            print(f"break at {buttons[i]}")
                            break
                if button == None:
                    log.info("Could not complete submission")
                    break
                elif submitted:
                    log.info("Application Submitted")
                    break

                time.sleep(random.uniform(1.5, 2.5))

        except Exception as e:
            log.info(e)
            log.info("cannot apply to this job")
            raise (e)

        return submitted
    
    def answer_questions(self):
        time.sleep(random.uniform(1.5, 2.5))

        questions = self.browser.find_elements(By.XPATH, "//*[contains(@class, 'jobs-easy-apply-form-element')]")
        log.info(f"Found {len(questions)} questions")
        
        for question in questions:
            try:
                label = question.find_element(By.XPATH, ".//label")
                log.info(f"Answering question: {label.text}")

                input_element = question.find_element(By.XPATH, f".//*[@id='{label.get_attribute('for')}']")
                log.info(f"Input type: {input_element.tag_name}")

                answer_provided = False

                if "first name" in label.text.lower():
                    input_element.send_keys(self.first_name)
                    answer_provided = True
                elif "last name" in label.text.lower():
                    input_element.send_keys(self.last_name)
                    answer_provided = True
                elif "address" in label.text.lower():
                    input_element.send_keys(self.address)
                    answer_provided = True
                elif "city" in label.text.lower():
                    input_element.send_keys(self.city)
                    answer_provided = True
                elif "state" in label.text.lower():
                    input_element.send_keys(self.state)
                    answer_provided = True
                elif "zip" in label.text.lower():
                    input_element.send_keys(self.zipcode)
                    answer_provided = True
                elif "country" in label.text.lower():
                    input_element.send_keys(self.country)
                    answer_provided = True
                elif "mobile phone number" in label.text.lower() or "primary phone number" in label.text.lower():
                    input_element.send_keys(self.phone_number)
                    answer_provided = True
                elif "years" in label.text.lower() or "how long" in label.text.lower():
                    input_element.send_keys(self.experience)
                    answer_provided = True
                elif "salary" in label.text.lower():
                    input_element.send_keys(self.salary)
                    answer_provided = True
                elif input_element.tag_name == "select":
                    options = input_element.find_elements(By.TAG_NAME, "option")
                    yes_selected = False
                    for option in options:
                        if "yes" in option.text.lower():
                            option.click()
                            yes_selected = True
                            break
                    if not yes_selected and options:
                        options[-1].click()  # Select the final option if 'yes' is not available
                elif input_element.tag_name == "input" and input_element.get_attribute("type") == "radio":
                    radio_buttons = question.find_elements(By.XPATH, ".//input[@type='radio']")
                    yes_selected = False
                    for radio_button in radio_buttons:
                        if radio_button.get_attribute("value").lower() == "yes":
                            label = radio_button.find_element(By.XPATH, "./following-sibling::label")
                            label.click()
                            yes_selected = True
                            break
                    if not yes_selected and radio_buttons:
                        final_radio_button = radio_buttons[-1]
                        final_label = final_radio_button.find_element(By.XPATH, "./following-sibling::label")
                        final_label.click()  # Select the final option if 'yes' is not available
                else:
                    log.info(f"Skipping question: {label.text}")

                if answer_provided:
                    time.sleep(random.uniform(2.0, 4.5))
                    
            except Exception as e:
                log.error(f"Error processing question: {str(e)}")
                continue


    def load_page(self, sleep=1):
        scroll_page = 0
        while scroll_page < 4000:
            self.browser.execute_script("window.scrollTo(0," + str(scroll_page) + " );")
            scroll_page += 200
            time.sleep(sleep)

        if sleep != 1:
            self.browser.execute_script("window.scrollTo(0,0);")
            time.sleep(sleep * 3)

        page = BeautifulSoup(self.browser.page_source, "lxml")
        return page

    def avoid_lock(self) -> None:
        x, _ = pyautogui.position()
        pyautogui.moveTo(x + 200, pyautogui.position().y, duration=1.0)
        pyautogui.moveTo(x, pyautogui.position().y, duration=0.5)
        pyautogui.keyDown('ctrl')
        pyautogui.press('esc')
        pyautogui.keyUp('ctrl')
        time.sleep(0.5)
        pyautogui.press('esc')

    def next_jobs_page(self, position, location, jobs_per_page):
        self.browser.get(
            "https://www.linkedin.com/jobs/search/?f_LF=f_AL&keywords=" +
            position + location + "&start=" + str(jobs_per_page))
        self.avoid_lock()
        log.info("Lock avoided.")
        self.load_page()
        return (self.browser, jobs_per_page)

    def finish_apply(self) -> None:
        self.browser.close()