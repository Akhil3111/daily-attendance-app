import os
from dotenv import load_dotenv

# Load environment variables from .env file for local testing
load_dotenv()

import time
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import json
import firebase_admin
from firebase_admin import credentials, firestore
from twilio.rest import Client

# Initialize the Flask application and enable CORS
app = Flask(__name__, static_folder='.')
CORS(app, resources={r"/*": {"origins": "https://daily-attendance-app-1.onrender.com"}})

# --- SECURITY WARNING ---
# This is a simplified approach for demonstration purposes.
# For a production application, use environment variables.

# Your Twilio Credentials
TWILIO_ACCOUNT_SID = "AC6815bba598db9422efa414b140621f91"
TWILIO_AUTH_TOKEN = "d53c5f473beeaa94278bcc5f8c3dff08"

# Your Firebase Service Account JSON (entire content as a string)
# IMPORTANT: This must be a single-line string with escaped newlines (\n)
FIREBASE_SERVICE_ACCOUNT_JSON = '{"type": "service_account","project_id": "daily-attendance-app-6cf76","private_key_id": "0471d3eae3af36237faaf47d308cf36270e58a01","private_key": "-----BEGIN PRIVATE KEY-----\\nMIIEuwIBADANBgkqhkiG9w0BAQEFAASCBKUwggShAgEAAoIBAQDfYOD2ToVbfni2\\n5m0z10VTEsV6toT5XaLesT2h/d3mNehMKqddnDQllHC00yvenl8laDIu3WqtyhEs\\nNhUNxSmo5MQc/TKcnhrL32mBbAU7GQtJuExXYzMQj6+0HWKKfrvizWYZFt39zqjv\\nauh9VnRY0js7fm7kfwpm9kg7qpIl/Rg8NQc+7sfUgyIBHpknci7nezk2tP30z8o5\\nvkfnNHWbxxKvGDYqo6m3+Vm7VYJGfM+IhIRDJG9lJyhAKgVIyhbQSnNh6XCQmmsX\\nT2hvJpR6LTh4fzmzMmwZi+jvCqCxe27PaTBvSFS+rLLaHWTAA+PsyTHc950UvsM1\\ntyqxcN27AgMBAAECgf881/nUQb/II/wCiG/g8ALx/0txkyD2cfR5Ne5St3oO7Vr3\\nQ6LtNewauf6z9Qnxzh0ooXXtXjlrbjUWnOGAuh8k6fYnph0SzOmLyzpzuPR+97Ti\\nhDAeeNqIRsOhQ6z1IKRd8dWQRP+YFjx/7fAQRAJQcDgbt1R9OdxSV99lNHJBGwRK\\njPBTSwl1mmHVHgVjON04ss1rlWzBW2p/TTY6HGUjhiF3BeVTUGQZgKr9dT0Wzlvz\\nDddkNjlAuyjuCfOLGLaDQumcEWsdhleOFUbZOVQG/0HBuwjDgZy7caxtxffLbSEJ\\nx7VCUZ0WYXLWc4hiGbrWyZa/6o6tUt/RlMu4kGkCgYEA9B2HzyuvQhX0qXdYStvs\\nKE05BL99c6p6Ic8yEY165FBS0CSC7XukZbYiZutLjLhLTC/XyE2xh/76iwmvV+JX\\n9IYSiwnHDRkxRSP0D8gwI6xPqGOJsASM7A6gxQ9McKJG10mQQkQq/oCd0d3gtDEY\\n9lwZ9BZHSY26q0bnz7IMlXUCgYEA6kDmH/BdT5VlYuSKEC+Ie0VxfpAjtn/9gCig\\ngsoAIH2xVTrhwYwxyByv01eW5sjx3P78/RsS4cnufkpDHJtMxX6Vvd6WMY0fYjR2\\nTdS8GZO8pK6s0irieUgESC3/KgL6MIlT44kDShY4JpRLEFQCHTkBWkggfB9uwFkP\\n4de50G8CgYBn3/T9O9p8pXkRb347hG9uCsYbdhw8zqrfnhnxDCHh6ygB97datIUU\\n3rau0qq4O2eXCLiqPB0yAFa+OSXKoL7Khw526Xcw5KppgE4HNSj+1QCkZ46cPqN0\\ngxj4IXVmbDb2vw/KktU0rKf7OI24PzgfBLvqeFxnOQ7YePiFEX93TQKBgH+sRYBs\\n2f6RF0QR+Wme7oz5KUVou/4wvfKGsgz2maEbwHYKdJavmUZO1EmkuHsqVCA13Z75\\njY4AJ/su8Gr7/Zi6SFTGpyd0mgFFRKFg6/AoxC0hgtG9S9f8N1E7uJGmM8QWZOFj\\ngKZ1e78THeJVVx2kPyd8ni/oVc2B/RUDJaQDAoGBAMwBCCIBssQLoaH3dkinm1Pj\\noYbjr0/5PgsRWkD+TtD0olqU6bjE2dgv6SHweRjWf6g9hTnJkFTnO8Tnd3dhFjnz\\nfk3v48N/9uobAJaenk92RiAkmZ5nfhHgKpuSM1I6hes3Q05dx30sHXC9wlFmIsDs\\nRLR+zmhfsUUu3KdI2dP0\\n-----END PRIVATE KEY-----\\n","client_email": "firebase-adminsdk-fbsvc@daily-attendance-app-6cf76.iam.gserviceaccount.com","client_id": "107598201014476323983","auth_uri": "https://accounts.google.com/o/oauth2/auth","token_uri": "https://oauth2.googleapis.com/token","auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40daily-attendance-app-6cf76.iam.gserviceaccount.com","universe_domain": "googleapis.com"}'

# Hardcoded path for ChromeDriver
# This path is where Render's system installs the WebDriver.
CHROMEDRIVER_PATH = "/usr/bin/chromedriver"

# Firebase credentials and app initialization
def initialize_firebase():
    """Initializes the Firebase Admin SDK from a hardcoded JSON string."""
    try:
        cred = credentials.Certificate(json.loads(FIREBASE_SERVICE_ACCOUNT_JSON))
        firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        print(f"Failed to initialize Firebase from hardcoded string: {e}")
        return None

db = initialize_firebase()

def send_whatsapp_message(to_number, message):
    """
    Sends a WhatsApp message using the Twilio API.
    """
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
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
        service = ChromeService(executable_path=CHROMEDRIVER_PATH)
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
        # If Firebase is not initialized, we fall back to a direct scrape.
        print("Warning: Firebase connection failed. Attempting direct scrape without database storage.")
        data = request.json
        username = data.get('username')
        password = data.get('password')
        whatsapp_number = data.get('whatsapp')

        if not username or not password:
            return jsonify({"error": "Username and password are required."}), 400

        scraped_data = get_attendance_data(username, password)
        
        if "error" in scraped_data:
            return jsonify(scraped_data), 500
        
        # Send WhatsApp message even if Firebase is not working.
        if whatsapp_number:
            message_body = f"📚 *Daily Attendance Report* 📚\n\n"
            message_body += f"✅ Total Attendance: *{scraped_data['total_percentage']}*\\n\\n"
            status_emojis = {"Present": "✅ Present", "Absent": "❌ Absent"}
            message_body += "*Subject-wise Breakdown:*\\n"
            for subject in scraped_data['subjects']:
                status_text = status_emojis.get(subject['status'], subject['status'])
                message_body += f"- {subject['subject']}: {status_text}\\n"
            send_whatsapp_message(whatsapp_number, message_body)

        return jsonify(scraped_data)

    # --- Firebase is working, proceed with the normal flow. ---
    data = request.json
    username = data.get('username')
    password = data.get('password')
    whatsapp_number = data.get('whatsapp')
    user_id = data.get('userId')
    app_id = data.get('appId')

    if not username or not password or not user_id or not app_id:
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
            message_body = f"📚 *Daily Attendance Report* 📚\n\n"
            message_body += f"✅ Total Attendance: *{scraped_data['total_percentage']}*\\n\\n"
            status_emojis = {"Present": "✅ Present", "Absent": "❌ Absent"}
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
