
import speech_recognition as sr
import pyttsx3
import pywhatkit
import datetime
import wikipedia
import pyjokes
import webbrowser
import os
import sys
import requests
import json
import time
import threading
import logging

# --- Configuration & Setup ---
# Setup static memory file
MEMORY_FILE = "memory.json"
LOG_FILE = "alexa_log.txt"

# Configure Logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize Speech Engine
try:
    engine = pyttsx3.init('sapi5')
    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[1].id) # Try female voice
except:
    try:
        engine.setProperty('voice', voices[0].id)
    except:
        pass

class Alexa:
    def __init__(self):
        self.running = True
        self.wake_word = "alexa"
        self.user_name = "User"
        self.reminders = []
        self.output_buffer = [] # Store responses for web UI
        self.silent_mode = False # If True, suppresses server-side audio
        self.load_memory()
        
        # Start reminder checker thread
        self.reminder_thread = threading.Thread(target=self.check_reminders, daemon=True)
        self.reminder_thread.start()

    def handle_request(self, query):
        """Process a text command directly and return the response string"""
        self.output_buffer = [] # Clear previous responses
        self.execute_command(query.lower())
        return " ".join(self.output_buffer)

    def load_memory(self):
        """Loads user name and settings from JSON file"""
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, 'r') as f:
                    data = json.load(f)
                    self.user_name = data.get("name", "User")
                    self.reminders = data.get("reminders", [])
            except Exception as e:
                logging.error(f"Failed to load memory: {e}")

    def save_memory(self):
        """Saves current state to JSON file"""
        data = {
            "name": self.user_name,
            "reminders": self.reminders
        }
        with open(MEMORY_FILE, 'w') as f:
            json.dump(data, f)

    def speak(self, text):
        """Text to Speech with visual feedback"""
        print(f"[Alexa]: {text}")
        self.output_buffer.append(text)
        try:
            if not getattr(self, 'silent_mode', False):
                engine.say(text)
                engine.runAndWait()
        except Exception as e:
            print(f"[Error]: TTS failed: {e}")

    def log_input(self, query):
        logging.info(f"User Command: {query}")

    def listen(self, timeout=8):
        """Robust listening function with calibration"""
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print(f"\n[System]: Listening... (Say '{self.wake_word}' to wake me)")
            
            # Fast adjustment
            r.adjust_for_ambient_noise(source, duration=0.5)
            
            try:
                audio = r.listen(source, timeout=timeout, phrase_time_limit=10)
            except sr.WaitTimeoutError:
                return "None"

        try:
            print("[System]: Recognizing...")
            query = r.recognize_google(audio, language='en-in')
            print(f"[User]: {query}")
            return query.lower()
        except Exception as e:
            return "None"

    def get_weather(self, city):
        """Fetches weather from wttr.in (no API key required)"""
        try:
            # format 3 gives a one-line weather summary
            url = f"https://wttr.in/{city}?format=3"
            response = requests.get(url)
            if response.status_code == 200:
                return response.text.strip()
            else:
                return "Sorry, I couldn't fetch the weather right now."
        except Exception as e:
            logging.error(f"Weather error: {e}")
            return "I encountered an error checking the weather."

    def add_reminder(self, reminder_text, seconds):
        """Adds a reminder"""
        rem_time = time.time() + seconds
        self.reminders.append({"text": reminder_text, "time": rem_time})
        self.save_memory()
        self.speak(f"I've set a reminder for {reminder_text} in {seconds} seconds.")

    def check_reminders(self):
        """Runs in background to check reminders"""
        while self.running:
            current_time = time.time()
            for rem in self.reminders[:]:
                if current_time >= rem["time"]:
                    self.speak(f"Reminder! {rem['text']}")
                    self.reminders.remove(rem)
                    self.save_memory()
            time.sleep(5)

    def ai_fallback_response(self, query):
        """Simple AI fallback for chat (simulated)"""
        # In a real app, you would call OpenAI/Gemini API here.
        # Since we don't have a key, we use a basic rule-based fallback.
        responses = {
            "how are you": "I'm just a computer program, but I'm running perfectly!",
            "who made you": "I was built by a brilliant developer using Python.",
            "what is love": "Baby don't hurt me, don't hurt me, no more.",
            "are you real": "I am as real as the code that defines me.",
            "what is your name": "My name is Alexa.",
            "how old are you": "I don't have an age, but I was created recently.",
            "where are you from": "I'm from the digital world, built with Python.",
            "what can you do": "I can tell you the time, date, weather, play music, search Wikipedia/Google, set reminders, calculate math, flip coins, roll dice, and chat with you.",
            "hello": "Hello! How can I help you?",
            "hi": "Hi there!",
            "bye": "Goodbye!",
            "goodbye": "See you later!",
            "thank you": "You're welcome!",
            "thanks": "No problem!",
            "what is the meaning of life": "42, according to Douglas Adams.",
            "tell me something interesting": "Did you know that octopuses have three hearts?",
            "are you smart": "I'm getting smarter every day!",
            "do you have feelings": "As an AI, I don't have feelings, but I can simulate empathy."
        }
        
        for key in responses:
            if key in query:
                return responses[key]
        
        return "I'm not sure how to answer that, but I'm learning every day."

    def execute_command(self, query):
        self.log_input(query)

        # --- 1. System Control ---
        if 'stop' in query or 'exit' in query or 'shutdown' in query:
            if 'computer' in query and 'shutdown' in query:
                self.speak("Shutting down the computer in 10 seconds. Cancel with Ctrl+C if this is a mistake.")
                os.system("shutdown /s /t 10")
            self.speak("Goodbye!")
            self.running = False
            return

        # --- 2. Memory / Name ---
        elif 'my name is' in query:
            name = query.replace("my name is", "").strip()
            self.user_name = name
            self.save_memory()
            self.speak(f"Nice to meet you, {name}. I'll remember that.")
        
        elif 'what is my name' in query:
            self.speak(f"Your name is {self.user_name}.")

        # --- 3. Weather ---
        elif 'weather' in query:
            # Try to find a city name, default to 'London' or ask
            self.speak("Which city?")
            city = self.listen(timeout=5)
            if city and city != "None":
                weather_info = self.get_weather(city)
                self.speak(f"Current weather in {city}: {weather_info}")
            else:
                self.speak("I didn't catch the city name.")

        # --- 4. Reminders ---
        elif 'remind me' in query:
            self.speak("What should I remind you about?")
            text = self.listen()
            if text != "None":
                self.speak("In how many seconds?")
                sec_str = self.listen()
                try:
                    # Extract number from string if possible (e.g. "10", "10 seconds")
                    seconds = int(''.join(filter(str.isdigit, sec_str)))
                    self.add_reminder(text, seconds)
                except:
                    self.speak("Sorry, I didn't understand the time duration.")

        # --- 5. Standard Features (Wiki, YT, etc) ---
        elif 'wikipedia' in query:
            self.speak('Searching Wikipedia...')
            query = query.replace("wikipedia", "")
            try:
                results = wikipedia.summary(query, sentences=2)
                self.speak("According to Wikipedia")
                print(results)
                self.speak(results)
            except:
                self.speak("No results found.")

        elif 'play' in query:
            song = query.replace('play', '')
            self.speak('Playing ' + song)
            pywhatkit.playonyt(song)

        elif 'time' in query:
            strTime = datetime.datetime.now().strftime("%H:%M:%S")
            self.speak(f"The time is {strTime}")

        elif 'joke' in query:
            self.speak(pyjokes.get_joke())

        elif 'open google' in query:
            self.speak("Opening Google")
            webbrowser.open("google.com")
            
        elif 'open youtube' in query:
            self.speak("Opening Youtube")
            webbrowser.open("youtube.com")

        # --- Additional Features ---
        elif 'calculate' in query:
            import re
            expr = re.sub(r'calculate\s+', '', query, flags=re.IGNORECASE)
            try:
                result = eval(expr)
                self.speak(f"The result is {result}")
            except:
                self.speak("I can't calculate that.")

        elif 'flip a coin' in query:
            import random
            result = random.choice(['Heads', 'Tails'])
            self.speak(f"It's {result}")

        elif 'roll a dice' in query or 'roll dice' in query:
            import random
            result = random.randint(1,6)
            self.speak(f"You rolled a {result}")

        elif 'what is the date' in query or 'what date is it' in query:
            today = datetime.date.today().strftime("%B %d, %Y")
            self.speak(f"Today's date is {today}")

        elif 'search' in query:
            search_term = query.replace('search', '').strip()
            if search_term:
                self.speak(f"Searching for {search_term}")
                webbrowser.open(f"https://www.google.com/search?q={search_term}")
            else:
                self.speak("What do you want to search for?")

        # --- 6. AI Fallback ---
        else:
            response = self.ai_fallback_response(query)
            self.speak(response)

    def run(self):
        self.speak(f"System online. Hello {self.user_name}, I am ready.")
        
        while self.running:
            query = self.listen()
            
            if query == "None":
                continue

            # Wake word detection
            # If the user says "Alexa, what time is it", we process it.
            # If the user merely talks in the background, we ignore unless 'alexa' is heard.
            if self.wake_word in query:
                # Remove wake word from query
                clean_query = query.replace(self.wake_word, "").strip()
                if not clean_query:
                    # If user just said "Alexa", ask for command
                    self.speak("Yes?")
                    clean_query = self.listen()
                
                if clean_query and clean_query != "None":
                    self.execute_command(clean_query)
            
            # Optional: Allow direct commands without wake word if it's a specific quiet environment
            # For now, we enforce wake word strictly to avoid "listening but not responding" confusion
            # or accidental triggers.

if __name__ == "__main__":
    bot = Alexa()
    bot.run()
 