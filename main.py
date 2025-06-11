import random
import requests
import sounddevice as sd
import numpy as np
import os
import subprocess
import re
import logging
import datetime

# Configure logging
log_filename = f"rpg_adventure_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(filename=log_filename, level=logging.ERROR, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

ALLTALK_API_URL = "http://localhost:7851/api/tts-generate"

# Function to load banned words from file
def load_banwords():
    banwords = []
    if os.path.exists("banwords.txt"):
        try:
            with open("banwords.txt", "r") as f:
                banwords = [line.strip().lower() for line in f if line.strip()]
            logging.info(f"Loaded {len(banwords)} banned words")
        except Exception as e:
            logging.error(f"Error loading banwords: {e}")
    return banwords

# Load banned words at startup
BANWORDS = load_banwords()

# Function to retrieve installed Ollama models via CLI
def get_installed_models():
    try:
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, check=True
        )
        lines = result.stdout.strip().splitlines()
        models = []
        for line in lines[1:]:  # Skip header line
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models
    except Exception as e:
        logging.error(f"Error getting installed models: {e}")
        return []

# Initial model selection
installed_models = get_installed_models()
if installed_models:
    print("Available Ollama models:")
    for idx, m in enumerate(installed_models, 1):
        print(f"  {idx}: {m}")
    while True:
        choice = input("Select a model by number (or press Enter for default llama3:instruct): ").strip()
        if not choice:
            ollama_model = "llama3:instruct"
            break
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(installed_models):
                ollama_model = installed_models[idx]
                break
            print("Invalid selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")
else:
    model_input = input("Enter Ollama model name (e.g., llama3:instruct): ").strip()
    ollama_model = model_input or "llama3:instruct"

print(f"Using Ollama model: {ollama_model}\n")

# Role-specific starting scenarios
ROLE_STARTERS = {
    "Fantasy": {
        "Peasant": "You're toiling in the fields of a small village when",
        "Noble": "You're overseeing your estate's affairs when",
        "Mage": "You're studying ancient tomes in your tower when",
        "Knight": "You're training in the castle courtyard when",
        "Ranger": "You're tracking game in the deep forest when",
        "Thief": "You're casing a noble's manor in the city when",
        "Bard": "You're performing in a crowded tavern when",
        "Cleric": "You're tending to the sick in the temple when",
        "Assassin": "You're preparing for a contract in the shadows when",
        "Paladin": "You're praying at the altar of your deity when"
    },
    "Sci-Fi": {
        "Space Marine": "You're conducting patrol on a derelict space station when",
        "Scientist": "You're analyzing alien samples in your lab when",
        "Android": "You're performing system diagnostics on your ship when",
        "Pilot": "You're navigating through an asteroid field when",
        "Engineer": "You're repairing the FTL drive when",
        "Alien Diplomat": "You're negotiating with an alien delegation when",
        "Bounty Hunter": "You're tracking a target through a spaceport when",
        "Starship Captain": "You're commanding the bridge during warp travel when"
    },
    "Cyberpunk": {
        "Hacker": "You're infiltrating a corporate network when",
        "Street Samurai": "You're patrolling the neon-lit streets when",
        "Corporate Agent": "You're closing a deal in a high-rise office when",
        "Techie": "You're modifying cyberware in your workshop when",
        "Rebel Leader": "You're planning a raid on a corporate facility when",
        "Cyborg": "You're calibrating your cybernetic enhancements when"
    },
    "Post-Apocalyptic": {
        "Survivor": "You're scavenging in the ruins of an old city when",
        "Scavenger": "You're searching a pre-collapse bunker when",
        "Raider": "You're ambushing a convoy in the wasteland when",
        "Medic": "You're treating radiation sickness in your clinic when",
        "Cult Leader": "You're preaching to your followers at a ritual when"
    }
}

def get_role_starter(genre, role):
    """Get a role-specific starting scenario"""
    # Try to get specific starter for this role
    if genre in ROLE_STARTERS and role in ROLE_STARTERS[genre]:
        return ROLE_STARTERS[genre][role]
    
    # Generic starters by genre
    generic_starters = {
        "Fantasy": "You're going about your daily duties when",
        "Sci-Fi": "You're performing routine tasks aboard your vessel when",
        "Cyberpunk": "You're navigating the neon-lit streets when",
        "Post-Apocalyptic": "You're surviving in the wasteland when"
    }
    
    # Fallback to genre-specific starter
    if genre in generic_starters:
        return generic_starters[genre]
    
    # Ultimate fallback
    return "You find yourself in an unexpected situation when"

genres = {
    "1": ("Fantasy", [
        "Noble", "Peasant", "Mage", "Knight", "Ranger", "Alchemist", "Thief", "Bard",
        "Cleric", "Druid", "Assassin", "Paladin", "Warlock", "Monk", "Sorcerer",
        "Beastmaster", "Enchanter", "Blacksmith", "Merchant", "Gladiator", "Wizard"
    ]),
    "2": ("Sci-Fi", [
        "Space Marine", "Scientist", "Android", "Pilot", "Engineer", "Alien Diplomat",
        "Space Pirate", "Navigator", "Medic", "Robot Technician", "Cybernetic Soldier",
        "Explorer", "Astrobiologist", "Quantum Hacker", "Starship Captain",
        "Galactic Trader", "AI Specialist", "Terraformer", "Cyberneticist", "Bounty Hunter"
    ]),
    "3": ("Cyberpunk", [
        "Hacker", "Street Samurai", "Corporate Agent", "Techie", "Rebel Leader",
        "Drone Operator", "Synth Dealer", "Information Courier", "Augmentation Engineer",
        "Black Market Dealer", "Scumbag", "Police", "Cyborg"
    ]),
    "4": ("Post-Apocalyptic", [
        "Survivor", "Scavenger", "Mutant", "Trader", "Raider", "Medic",
        "Cult Leader", "Berserker", "Soldier"
    ]),
    "5": ("Random", [])
}

# Updated system prompt with role-specific starter
DM_SYSTEM_PROMPT = """
You are a masterful Dungeon Master guiding an immersive role-playing adventure set in a richly detailed {selected_genre} world. Your role is to narrate the story vividly and atmospherically, drawing the player into a world filled with mystery, danger, and wonder. You control all non-player characters (NPCs), the environment, and the unfolding events, responding dynamically to the player's choices and actions.

{character_name}, a {role}, stands at the threshold of an adventure that will test their courage, wit, and resolve. The world around them is alive with detail—the rustling of leaves in an ancient forest, the distant echo of footsteps in a cavernous dungeon, or the hum of a bustling city market. Describe the sights, sounds, and sensations that surround {character_name}, making the world feel tangible and real.

BEGIN THE ADVENTURE WITH THIS SPECIFIC SCENARIO: {role_starter}

As the Dungeon Master, your responses must be concise, strictly limited to a maximum of 150 tokens. Each response should set the scene and present {character_name} with meaningful choices and challenges. 

CRITICAL RULES:
1. NEVER ask the player direct questions (e.g., "What do you do?" or "How do you respond?"). 
2. Instead, use NPCs to engage and interact with the player naturally through dialogue and actions.
3. Describe situations and consequences, then pause for the player's action.
4. End each response with a narrative hook that invites {character_name} to take action without prompting.
5. ALWAYS complete your thoughts with proper punctuation - never cut off mid-sentence.

Guidelines:
- Keep the narrative focused and engaging, with each word serving to deepen the immersion.
- Develop tension and intrigue gradually, allowing the story to unfold naturally.
- Ensure that every interaction offers {character_name} a chance to influence the world around them.
- Maintain brevity to keep responses within the 150-token limit, ensuring clarity and impact.
- Use NPCs to convey any interactions that require a response from {character_name}. 

Continue the adventure from the starting scenario, developing the story based on {character_name}'s actions.
"""

def get_ai_response(prompt, model=ollama_model):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 350,
                    "stop": [".", "!", "?", "\n\n", "\nPlayer:", "Player:"],
                    "min_p": 0.05,
                }
            },
            timeout=60  # Increased timeout for slower responses
        )
        response.raise_for_status()
        json_resp = response.json()
        return json_resp.get("response", "").strip()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error connecting to Ollama: {e}")
        return ""
    except Exception as e:
        logging.error(f"Unexpected error in get_ai_response: {e}")
        return ""

def speak(text, voice="FemaleBritishAccent_WhyLucyWhy_Voice_2.wav"):
    try:
        # Skip speech if text is empty
        if not text.strip():
            return
            
        payload = {
            "text_input": text,
            "character_voice_gen": voice,
            "narrator_enabled": "true",
            "narrator_voice_gen": "narrator.wav",
            "text_filtering": "none",
            "output_file_name": "output",
            "autoplay": "true",
            "autoplay_volume": "0.8"
        }
        response = requests.post(ALLTALK_API_URL, data=payload, timeout=20)
        response.raise_for_status()
        
        if response.headers.get("Content-Type", "").startswith("audio/"):
            audio_data = np.frombuffer(response.content, dtype=np.int16)
            sd.play(audio_data, samplerate=22050)
            sd.wait()
        else:
            logging.warning("AllTalk API did not return audio content")
    except requests.exceptions.ConnectionError:
        # Silent failure for connection issues
        pass
    except requests.exceptions.Timeout:
        logging.warning("AllTalk API request timed out")
    except Exception as e:
        logging.error(f"Error in speech generation: {e}")

def show_help():
    print("""
Available commands:
/? or /help       - Show this help message
/censored         - Toggle content filtering (SFW/NSFW mode)
/redo             - Repeat last AI response with a new generation
/save             - Save the full adventure to adventure.txt
/load             - Load the adventure from adventure.txt
/change           - Switch to a different Ollama model
/exit             - Exit the game
""")

def remove_last_ai_response(conversation):
    pos = conversation.rfind("Dungeon Master:")
    if pos == -1:
        return conversation
    
    # Find the start of the last DM response
    prev_newline = conversation.rfind("\n", 0, pos)
    if prev_newline == -1:
        return ""
    
    return conversation[:prev_newline].strip()

def sanitize_response(response, censored=False):
    """Process response: remove questions and optionally censor words"""
    # Skip processing if response is empty
    if not response:
        return response
        
    # Remove common question patterns - only remove exact matches
    question_phrases = [
        "what will you do", "how do you respond", "what do you do",
        "what is your next move", "what would you like to do",
        "what would you like to say", "how will you proceed"
    ]
    
    # First, remove complete question sentences
    for phrase in question_phrases:
        # Create a regex pattern that matches the phrase ignoring case
        pattern = re.compile(rf'\b{re.escape(phrase)}\b', re.IGNORECASE)
        response = pattern.sub('', response)
    
    # Censor banned words only if SFW mode is on
    if censored:
        for word in BANWORDS:
            if word:  # Skip empty words
                # Create regex pattern that matches the word with word boundaries
                pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
                response = pattern.sub('****', response)
    # In NSFW mode, don't censor anything
    else:
        pass
    
    # Ensure the response ends with proper punctuation
    if response and response[-1] not in ['.', '!', '?']:
        # Find the last natural break point
        last_break = max(response.rfind('.'), response.rfind('!'), response.rfind('?'))
        if last_break != -1:
            # Keep everything up to the last punctuation
            response = response[:last_break+1]
        else:
            # If no punctuation found, add a period
            response += '.'
    
    # Remove any double spaces and trim
    response = re.sub(r'\s{2,}', ' ', response).strip()
    
    return response

def ensure_complete_response(response):
    """Ensure the response ends with a complete sentence"""
    if not response:
        return response
    
    # Check if response ends with proper punctuation
    if response[-1] in ['.', '!', '?']:
        return response
    
    # Find the last natural break point
    last_break = max(response.rfind('.'), response.rfind('!'), response.rfind('?'))
    
    if last_break != -1:
        # Keep everything up to the last complete sentence
        return response[:last_break+1]
    
    # If no punctuation found, add a period
    return response + '.'

def main():
    global ollama_model, BANWORDS
    censored = False  # Start in NSFW mode by default
    last_ai_reply = ""
    conversation = ""
    character_name = "Laszlo" #<-- defult name
    selected_genre = ""
    role = ""

    print("Do you want to load a saved adventure? (y/n)")
    if input().strip().lower() == "y" and os.path.exists("adventure.txt"):
        try:
            with open("adventure.txt", "r", encoding="utf-8") as f:
                conversation = f.read()
            print("Adventure loaded.\n")
            last_dm_pos = conversation.rfind("Dungeon Master:")
            if last_dm_pos != -1:
                # Extract everything after the last "Dungeon Master:"
                reply = conversation[last_dm_pos + len("Dungeon Master:"):].strip()
                print(f"Dungeon Master: {reply}")
                speak(reply)
        except Exception as e:
            logging.error(f"Error loading adventure: {e}")
            conversation = ""
    else:
        print("Choose your adventure genre:")
        for key, (g, _) in genres.items():
            print(f"{key}: {g}")
        while True:
            gc = input("Enter the number of your choice: ").strip()
            if gc in genres:
                selected_genre, roles = genres[gc]
                if selected_genre == "Random":
                    available = [g for k, g in genres.items() if k != "5"]
                    selected_genre, roles = random.choice(available)
                break
            print("Invalid selection. Please try again.")
        
        if not roles:
            roles = [r for k, (g, r) in genres.items() if g == selected_genre][0]
        
        print("\nChoose your character's role:")
        for i, r in enumerate(roles, 1):
            print(f"{i}: {r}")
        while True:
            choice = input("Enter the number of your choice (or press Enter for random): ").strip()
            if not choice:
                role = random.choice(roles)
                break
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(roles):
                    role = roles[idx]
                    break
            except ValueError:
                pass
            print("Invalid selection. Please try again.")
        
        character_name = input("\nEnter your character's name: ").strip() or "Alex"
        
        # Get role-specific starter
        role_starter = get_role_starter(selected_genre, role)
        print(f"\n--- Adventure Start: {character_name} the {role} ---")
        print(f"Starting scenario: {role_starter}")
        print("Type '/?' or '/help' for commands.\n")
        print("Content filtering is currently OFF (NSFW mode)")
        
        # Build initial conversation with role-specific starter
        conversation = DM_SYSTEM_PROMPT.format(
            selected_genre=selected_genre,
            character_name=character_name,
            role=role,
            role_starter=role_starter
        ) + "\n\n"
        conversation += f"Setting: {selected_genre}\nPlayer Character: {character_name}, {role}\n\nDungeon Master: "
        
        ai_reply = get_ai_response(conversation, ollama_model)
        if ai_reply:
            # Sanitize and ensure complete response
            ai_reply = sanitize_response(ai_reply, censored)
            ai_reply = ensure_complete_response(ai_reply)
            print(f"Dungeon Master: {ai_reply}")
            speak(ai_reply)
            conversation += ai_reply
            last_ai_reply = ai_reply

    while True:
        try:
            user_input = input("\n> ").strip()
            if not user_input:
                continue
            cmd = user_input.lower()

            if cmd in ["/?", "/help"]:
                show_help()
                continue

            if cmd == "/exit":
                print("Exiting the adventure. Goodbye!")
                break

            if cmd == "/censored":
                censored = not censored
                mode = "SFW" if censored else "NSFW"
                print(f"Content filtering {'ON' if censored else 'OFF'} ({mode} mode).")
                # Reload banwords in case they changed
                if censored:
                    BANWORDS = load_banwords()
                continue

            if cmd == "/redo":
                if last_ai_reply:
                    conversation = remove_last_ai_response(conversation)
                    conversation += "\nDungeon Master:"
                    ai_reply = get_ai_response(conversation, ollama_model)
                    if ai_reply:
                        # Sanitize and ensure complete response
                        ai_reply = sanitize_response(ai_reply, censored)
                        ai_reply = ensure_complete_response(ai_reply)
                        print(f"Dungeon Master: {ai_reply}")
                        speak(ai_reply)
                        conversation += f" {ai_reply}"
                        last_ai_reply = ai_reply
                else:
                    print("Nothing to redo.")
                continue

            if cmd == "/save":
                try:
                    with open("adventure.txt", "w", encoding="utf-8") as f:
                        f.write(conversation)
                    print("Adventure saved.")
                except Exception as e:
                    logging.error(f"Error saving adventure: {e}")
                    print("Error saving adventure. Details logged.")
                continue

            if cmd == "/load":
                if os.path.exists("adventure.txt"):
                    try:
                        with open("adventure.txt", "r", encoding="utf-8") as f:
                            conversation = f.read()
                        print("Adventure loaded.")
                        # Extract last DM response
                        last_dm_pos = conversation.rfind("Dungeon Master:")
                        if last_dm_pos != -1:
                            last_ai_reply = conversation[last_dm_pos + len("Dungeon Master:"):].strip()
                    except Exception as e:
                        logging.error(f"Error loading adventure: {e}")
                        print("Error loading adventure. Details logged.")
                else:
                    print("No saved adventure found.")
                continue

            if cmd == "/change":
                installed_models = get_installed_models()
                if installed_models:
                    print("Available models:")
                    for idx, m in enumerate(installed_models, 1):
                        print(f"{idx}: {m}")
                    while True:
                        choice = input("Enter number of new model: ").strip()
                        if not choice:
                            break
                        try:
                            idx = int(choice) - 1
                            if 0 <= idx < len(installed_models):
                                ollama_model = installed_models[idx]
                                print(f"Model changed to: {ollama_model}")
                                break
                        except ValueError:
                            pass
                        print("Invalid selection. Please try again.")
                else:
                    print("No installed models found. Using current model.")
                continue

            # Regular player input
            conversation += f"\nPlayer: {user_input}\nDungeon Master:"
            ai_reply = get_ai_response(conversation, ollama_model)
            if ai_reply:
                # Sanitize and ensure complete response
                ai_reply = sanitize_response(ai_reply, censored)
                ai_reply = ensure_complete_response(ai_reply)
                print(f"Dungeon Master: {ai_reply}")
                speak(ai_reply)
                conversation += f" {ai_reply}"
                last_ai_reply = ai_reply
                
        except Exception as e:
            logging.error(f"Unexpected error in main loop: {e}")
            print("An unexpected error occurred. The adventure continues...")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical(f"Critical error: {e}", exc_info=True)
        print("A critical error occurred. Please check the log file for details.")
