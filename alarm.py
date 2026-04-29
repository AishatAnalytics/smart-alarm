import os
import json
import boto3
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

ses = boto3.client('ses', region_name=os.getenv('AWS_REGION'))

def get_weather():
    city = os.getenv('CITY')
    api_key = os.getenv('WEATHER_API_KEY')
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=imperial"
    
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        return {
            'temp': round(data['main']['temp']),
            'feels_like': round(data['main']['feels_like']),
            'description': data['weather'][0]['description'],
            'humidity': data['main']['humidity'],
            'wind_speed': round(data['wind']['speed'])
        }
    except Exception as e:
        print(f"Weather fetch failed: {e}")
        return None

def calculate_wake_time(weather, default_wake="6:00 AM"):
    adjustments = []
    extra_minutes = 0

    if weather:
        if weather['temp'] < 32:
            extra_minutes += 15
            adjustments.append("Freezing temps — extra 15min for warming up car")
        elif weather['temp'] > 95:
            extra_minutes += 10
            adjustments.append("Extreme heat — extra 10min to cool down car")

        if weather['wind_speed'] > 20:
            extra_minutes += 10
            adjustments.append("High winds — extra 10min for slow traffic")

        if 'rain' in weather['description'] or 'snow' in weather['description']:
            extra_minutes += 20
            adjustments.append("Rain/snow — extra 20min for slow commute")

    if extra_minutes > 0:
        wake_time = f"5:{60 - extra_minutes:02d} AM" if extra_minutes < 60 else "5:00 AM"
        return wake_time, adjustments
    
    return default_wake, ["Normal conditions — standard wake time"]

def send_alarm(weather, wake_time, adjustments):
    weather_text = f"""
Current conditions in {os.getenv('CITY')}:
Temperature: {weather['temp']}F (feels like {weather['feels_like']}F)
Conditions: {weather['description']}
Humidity: {weather['humidity']}%
Wind: {weather['wind_speed']} mph
""" if weather else "Weather data unavailable"

    message = f"""
SMART ALARM CLOCK
=================
Date: {datetime.now().strftime('%Y-%m-%d')}

RECOMMENDED WAKE TIME: {wake_time}

ADJUSTMENTS MADE:
{chr(10).join([f"- {a}" for a in adjustments])}

WEATHER UPDATE:
{weather_text}

Smart Alarm Clock
    """

    try:
        ses.send_email(
            Source=os.getenv('YOUR_EMAIL'),
            Destination={'ToAddresses': [os.getenv('YOUR_EMAIL')]},
            Message={
                'Subject': {'Data': f"Smart Alarm — Wake up at {wake_time}"},
                'Body': {'Text': {'Data': message}}
            }
        )
        print(f"Alarm sent to {os.getenv('YOUR_EMAIL')}")
    except Exception as e:
        print(f"Email failed: {e}")

def run():
    print("Smart Alarm Clock")
    print("=================\n")

    print("Step 1: Fetching weather...")
    weather = get_weather()
    if weather:
        print(f"Temperature: {weather['temp']}F")
        print(f"Conditions: {weather['description']}")
        print(f"Wind: {weather['wind_speed']} mph")

    print("\nStep 2: Calculating wake time...")
    wake_time, adjustments = calculate_wake_time(weather)
    print(f"Recommended wake time: {wake_time}")
    for adj in adjustments:
        print(f"  - {adj}")

    print("\nStep 3: Sending alarm...")
    send_alarm(weather, wake_time, adjustments)

    report = {
        'timestamp': datetime.now().isoformat(),
        'weather': weather,
        'wake_time': wake_time,
        'adjustments': adjustments
    }

    with open('alarm_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    print("Report saved to alarm_report.json")
    print("\nSmart Alarm Clock complete!")

if __name__ == "__main__":
    run()