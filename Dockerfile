Use the official Python base image
FROM python:3.12-slim

Install system dependencies for headless Chrome
RUN apt-get update && apt-get install -y 

wget 

gnupg 

&& wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - 

&& echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list 

&& apt-get update && apt-get install -y 

google-chrome-stable 

--no-install-recommends 

&& rm -rf /var/lib/apt/lists/*

Set the working directory in the container
WORKDIR /app

Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

Copy the rest of the application code
COPY . .

Expose the port the Flask app will run on
EXPOSE 5000

Set the command to run the Flask app
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]