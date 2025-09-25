import os
from dotenv import load_dotenv
import time
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import json
import firebase_admin
from firebase_admin import credentials, firestore
from twilio.rest import Client

# Load environment variables from .env file for local testing
load_dotenv()

# Initialize the Flask application and enable CORS
app = Flask(__name__, static_folder='.')
CORS(app, resources={r"/*": {"origins": "https://daily-attendance-app-1.onrender.com"}})

# Firebase credentials and app initialization
def initialize_firebase():
    """Initializes the Firebase Admin SDK from a JSON string in an environment variable."""
    service_account_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    if not service_account_json:
        print("Error: FIREBASE_SERVICE_ACCOUNT environment variable not found.")
        return None
    
    try:
        cred = credentials.Certificate(json.loads(service_account_json))
        firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        print(f"Failed to initialize Firebase from environment variable: {e}")
        return None

db = initialize_firebase()

def send_whatsapp_message(to_number, message):
    """
    Sends a WhatsApp message using the Twilio API.
    """
    try:
        # Get Twilio credentials from environment variables for security.
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

        if not account_sid or not auth_token:
            print("Error: Twilio credentials not found in environment variables.")
            return False

        client = Client(account_sid, auth_token)

        # Your Twilio WhatsApp-enabled phone number
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
        
        time.sleep(3)

        print("Clicking attendance button...")
        a_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="ctl00_ContentPlaceHolder1_divAttendance"]/div[3]/a/div[2]'))
        )
        a_btn.click()
        
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

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/scrape-attendance', methods=['POST'])
def scrape_attendance():
    """
    API endpoint to trigger the web scraping.
    It saves credentials to Firestore, scrapes the data, and saves it back.
    """
    if not db:
        return jsonify({"error": "Firebase is not initialized. Check your service account key."}), 500

    data = request.json
    username = data.get('username')
    password = data.get('password')
    whatsapp_number = data.get('whatsapp')
    user_id = data.get('userId')
    app_id = data.get('appId')

    if not username or not password or not user_id or not app_id:
        # If any of the required fields are missing, it means the request is invalid.
        return jsonify({"error": "Missing required data."}), 400

    try:
        # Save credentials to Firestore
        creds_ref = db.collection('artifacts').document(app_id).collection('users').document(user_id).collection('credentials').document('credentials')
        creds_ref.set({
            'username': username,
            'password': password,
            'whatsapp': whatsapp_number
        })

        # Perform the scraping
        scraped_data = get_attendance_data(username, password)
        
        if "error" in scraped_data:
            return jsonify(scraped_data), 500
        
        # Save the scraped data back to Firestore
        attendance_doc_ref = db.collection('artifacts').document(app_id).collection('users').document(user_id).collection('attendance_data').document('attendance_data')
        attendance_doc_ref.set(scraped_data)

        # Send WhatsApp message
        if whatsapp_number:
            # Create a more readable message format
            message_body = f"📚 *Daily Attendance Report* 📚\n\n"
            message_body += f"✅ Total Attendance: *{scraped_data['total_percentage']}*\\n\\n"
            
            # Use emojis for statuses
            status_emojis = {
                "Present": "✅ Present",
                "Absent": "❌ Absent"
            }
            
            # Create a clean list of subjects with statuses
            message_body += "*Subject-wise Breakdown:*\\n"
            for subject in scraped_data['subjects']:
                status_text = status_emojis.get(subject['status'], subject['status'])
                message_body += f"- {subject['subject']}: {status_text}\\n"
                
            send_whatsapp_message(whatsapp_number, message_body)

        return jsonify(scraped_data)

    except Exception as e:
        print(f"An error occurred in the API endpoint: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
