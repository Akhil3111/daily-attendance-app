import os
from dotenv import load_dotenv
import time
from flask import jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import firebase_admin
from firebase_admin import credentials, firestore
from twilio.rest import Client

# Load environment variables from .env file
load_dotenv()

# Firebase credentials and app initialization
def initialize_firebase():
    """Initializes the Firebase Admin SDK."""
    firebase_key_path = "firebase-key.json"
    if not os.path.exists(firebase_key_path):
        print(f"Error: Firebase service account key not found at '{firebase_key_path}'.")
        print("Please download it from the Firebase Console and place it in this directory.")
        return None
        
    try:
        cred = credentials.Certificate(firebase_key_path)
        firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        print(f"Failed to initialize Firebase: {e}")
        return None

db = initialize_firebase()

def send_whatsapp_message(to_number, message):
    """
    Sends a WhatsApp message using the Twilio API.
    """
    try:
        # Get Twilio credentials from environment variables for security.
        # This prevents hardcoding secrets in your code.
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

        if not account_sid or not auth_token:
            print("Error: Twilio credentials not found in environment variables.")
            return False

        client = Client(account_sid, auth_token)

        # Your Twilio WhatsApp-enabled phone number
        # Example: 'whatsapp:+14155238886'
        twilio_number = "whatsapp:+14155238886"
        
        message_sent = client.messages.create(
            from_=twilio_number,
            body=message,
            to=f'whatsapp:{to_number}'
        )
        print(f"WhatsApp message sent with SID: {message_sent.sid}")
        return True
    except Exception as e:
        print(f"Failed to send WhatsApp message: {e}")
        return False

def get_attendance_data(username, password):
    """
    Uses Selenium to scrape attendance data from the college website.
    """
    print("Starting Selenium web scraping...")
    
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    
    driver = None
    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("WebDriver initialized. Navigating to login page...")
        driver.get("https://login.vardhaman.org/")
        wait = WebDriverWait(driver, 30)

        print("Filling in username and password...")
        uname_field = wait.until(EC.element_to_be_clickable((By.NAME, 'txtuser')))
        pass_field = wait.until(EC.element_to_be_clickable((By.NAME, 'txtpass')))
        uname_field.send_keys(username)
        pass_field.send_keys(password)
        
        print("Clicking login button...")
        l_button = wait.until(EC.element_to_be_clickable((By.NAME, 'btnLogin')))
        l_button.click()

        # Adding a short delay to allow the page to fully load and pop-ups to appear
        time.sleep(3)

        try:
            print("Checking for pop-up...")
            c_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="ctl00_ContentPlaceHolder1_PopupCTRLMain_Image2"]'))
            )
            c_btn.click()
            print("Pop-up closed.")
        except TimeoutException:
            print("No pop-up found, continuing...")
        
        # Adding a small, strategic delay to ensure the dashboard content has time to load
        time.sleep(3)

        # Now we click the button to get the detailed attendance list
        print("Clicking attendance button...")
        a_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="ctl00_ContentPlaceHolder1_divAttendance"]/div[3]/a/div[2]'))
        )
        a_btn.click()
        
        # Now we scrape the total percentage directly from the main attendance page
        total_percentage = "N/A"
        try:
            print("Waiting for total attendance percentage...")
            total_percentage_element = wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, '.attendance-count'))
            )
            total_percentage = total_percentage_element.text
            print(f"Found total percentage: {total_percentage}")
        except TimeoutException:
            print("Total percentage element not found. It may be loading slowly or the page structure has changed.")
        
        
        print("Waiting for attendance items list...")
        attendance_items = wait.until(
            EC.presence_of_all_elements_located((
                By.CSS_SELECTOR,
                ".atten-sub.bus-stops ul li"
        ))
)
        
        
        attendance_list = []
        for item in attendance_items:
            try:
                subject = item.find_element(By.TAG_NAME, "h5").text
                time_slot = item.find_elements(By.CSS_SELECTOR, ".stp-detail p.text-primary")[0].text
                faculty = item.find_elements(By.CSS_SELECTOR, ".fac-status p.text-primary")[0].text
                status = item.find_element(By.CSS_SELECTOR, ".fac-status .status").text

                attendance_list.append({
                    "subject": subject,
                    "time_slot": time_slot,
                    "faculty": faculty,
                    "status": status
                })
            except (NoSuchElementException, IndexError) as e:
                print(f"Skipping malformed attendance item: {e}")
                continue

        print("Scraping successful. Returning data.")
        return {"subjects": attendance_list, "total_percentage": total_percentage}
        
    except TimeoutException:
        print("Timeout while waiting for elements. The page structure may have changed.")
        return {"error": "Failed to load page elements. The login or page structure may have changed."}
    except WebDriverException as e:
        print(f"WebDriver error: {e}")
        return {"error": "A WebDriver error occurred. Make sure the driver is installed and accessible."}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {"error": "An unexpected error occurred during scraping."}
    finally:
        if driver:
            print("Closing WebDriver.")
            driver.quit()

def process_all_users():
    """
    Fetches all user credentials and runs the attendance check for each one.
    """
    if not db:
        print("Database not initialized. Exiting.")
        return

    # Use a dummy appId since the runner script doesn't have one from a web request.
    app_id = "your-app-id" # Use your Firebase project ID here.

    try:
        users_ref = db.collection('artifacts').document(app_id).collection('users')
        users_docs = users_ref.stream()
        
        for user_doc in users_docs:
            user_id = user_doc.id
            print(f"Processing attendance for user: {user_id}")
            
            # Fetch credentials for the user
            creds_ref = user_doc.collection('credentials').document('credentials')
            creds_doc = creds_ref.get()

            if creds_doc.exists:
                creds = creds_doc.to_dict()
                username = creds.get('username')
                password = creds.get('password')
                whatsapp_number = creds.get('whatsapp')

                if username and password and whatsapp_number:
                    scraped_data = get_attendance_data(username, password)
                    
                    if "error" not in scraped_data:
                        # Save the scraped data
                        attendance_doc_ref = user_doc.collection('attendance_data').document('attendance_data')
                        attendance_doc_ref.set(scraped_data)

                        # Send WhatsApp message
                        message_body = f"📚 *Daily Attendance Report* 📚\n\n"
                        message_body += f"✅ Total Attendance: *{scraped_data['total_percentage']}*\n\n"
                        status_emojis = {"Present": "✅ Present", "Absent": "❌ Absent"}
                        message_body += "*Subject-wise Breakdown:*\n"
                        for subject in scraped_data['subjects']:
                            status_text = status_emojis.get(subject['status'], subject['status'])
                            message_body += f"- {subject['subject']}: {status_text}\n"
                            
                        send_whatsapp_message(whatsapp_number, message_body)
                    else:
                        print(f"Failed to scrape data for user {user_id}: {scraped_data['error']}")
                else:
                    print(f"Skipping user {user_id}: Missing credentials.")
            else:
                print(f"Skipping user {user_id}: Credentials document not found.")

    except Exception as e:
        print(f"An unexpected error occurred while processing all users: {e}")

if __name__ == '__main__':
    process_all_users()
