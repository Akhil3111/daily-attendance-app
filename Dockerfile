FROM python:3.12-slim

Install system dependencies for headless Chrome
RUN apt-get update && apt-get install -y gnupg wget unzip libnss3 libxss1 libappindicator3-1 libasound2 libatk-bridge2.0-0 libgtk-3-0 libcups2 libgdk-pixbuf2.0-0 libgbm1 libxkbcommon-x11-0 --no-install-recommends

Install Chrome Browser
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/trusted.gpg.d/google.gpg 

&& echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
RUN apt-get update && apt-get install -y google-chrome-stable

Set up working directory
WORKDIR /app

Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

Copy the rest of the application code
COPY . .

Expose the port for the Flask app
EXPOSE 5000

Set the command to run the Flask app
CMD ["python", "app.py"]
