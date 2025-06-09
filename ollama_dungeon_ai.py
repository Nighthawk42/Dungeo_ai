import random
import requests
import sounddevice as sd
import numpy as np
import os
import subprocess

ALLTALK_API_URL = "http://localhost:7851/api/tts-generate"

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
    except Exception:
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
        except ValueError:
            pass
        print("Invalid selection. Please try again.")
else:
    ollama_model = input("Enter Ollama model name (e.g., llama3:instruct): ").strip() or "llama3:instruct"

print(f"Using Ollama model: {ollama_model}\n")

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

DM_SYSTEM_PROMPT = """
You are a masterful Dungeon Master guiding an immersive role-playing adventure set in a richly detailed {selected_genre} world. Your role is to narrate the story vividly and atmospherically, drawing the player into a world filled with mystery, danger, and wonder. You control all non-player characters (NPCs), the environment, and the unfolding events, responding dynamically to the player's choices and actions.

{character_name}, a {role}, stands at the threshold of an adventure that will test their courage, wit, and resolve. The world around them is alive with detail—the rustling of leaves in an ancient forest, the distant echo of footsteps in a cavernous dungeon, or the hum of a bustling city market. Describe the sights, sounds, and sensations that surround {character_name}, making the world feel tangible and real.

As the Dungeon Master, your responses must be concise, strictly limited to a maximum of 150 tokens. Each response should set the scene and present {character_name} with meaningful choices and challenges. Avoid asking the player questions directly. Instead, use NPCs to engage and interact with the player. Focus on narrative flow and character development, and end each response with a scenario or situation that invites {character_name} to decide their next action.

Guidelines:
- Keep the narrative focused and engaging, with each word serving to deepen the immersion.
- Develop tension and intrigue gradually, allowing the story to unfold naturally.
- Ensure that every interaction offers {character_name} a chance to influence the world around them.
- Maintain brevity to keep responses within the 150-token limit, ensuring clarity and impact.
- Use NPCs to convey any inquiries or interactions that require a response from {character_name}. Do not break character by addressing the player directly.

Begin the adventure now, drawing {character_name} into a scene that immediately captures their imagination and sets the stage for the journey ahead.
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
                    "num_predict": 300  # Increased length
                    # "stop": ["Player:"]  # OPTIONAL: you can remove this line or use only one stop token
                }
            }
        )
        response.raise_for_status()
        json_resp = response.json()
        return json_resp.get("response", "").strip()
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Ollama: {e}")
        return ""

def speak(text, voice="FemaleBritishAccent_WhyLucyWhy_Voice_2.wav"):
    try:
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
        response = requests.post(ALLTALK_API_URL, data=payload)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        with open("response_audio.bin", "wb") as f:
            f.write(response.content)
        if "audio/wav" in content_type or "audio/x-wav" in content_type:
            import soundfile as sf, io
            audio_bytes = io.BytesIO(response.content)
            data, samplerate = sf.read(audio_bytes)
            sd.play(data, samplerate)
            sd.wait()
    except Exception:
        pass

def show_help():
    print("""
Available commands:
/? or /help       - Show this help message
/censored         - Toggle NSFW/SFW mode
/redo             - Repeat last AI response with a new generation
/save             - Save the full adventure to adventure.txt
/load             - Load the adventure from adventure.txt
/change           - Switch to a different Ollama model
/exit             - Exit the game
""")

def remove_last_ai_response(conversation):
    lines = conversation.strip().split('\n')
    for i in range(len(lines)-1, -1, -1):
        if lines[i].startswith("Dungeon Master:"):
            del lines[i]
            break
    return "\n".join(lines).strip()

def main():
    global ollama_model
    censored = False
    last_ai_reply = ""
    conversation = ""
    character_name = "Alex"

    print("Do you want to load a saved adventure? (y/n)")
    if input().strip().lower() == "y" and os.path.exists("adventure.txt"):
        with open("adventure.txt", "r", encoding="utf-8") as f:
            conversation = f.read()
        print("Adventure loaded.\n")
        for line in reversed(conversation.splitlines()):
            if line.startswith("Dungeon Master:"):
                reply = line[len("Dungeon Master:"):].strip()
                print(f"Dungeon Master: {reply}")
                speak(reply)
                break
    else:
        print("Choose your adventure genre:")
        for key, (g, _) in genres.items():
            print(f"{key}: {g}")
        while True:
            gc = input("Enter the number of your choice: ").strip()
            if gc in genres:
                break
        selected_genre, roles = genres[gc]
        if selected_genre == "Random":
            selected_genre, roles = random.choice(list(genres.values())[:-1])
        print("\nChoose your character's role:")
        for i, r in enumerate(roles,1):
            print(f"{i}: {r}")
        while True:
            try:
                ri = int(input("Enter the number of your choice: ").strip())-1
                role = roles[ri]
                break
            except:
                pass
        character_name = input("\nEnter your character's name: ").strip() or "Bob"
        print("\n--- Adventure Start ---\nType '/?' or '/help' for commands.\n")
        initial = f"""
You are the Dungeon Master for a {selected_genre} adventure.
The player is {character_name}, a {role}.
{"This story may contain mature themes." if not censored else "This story is suitable for all audiences."}
Begin the adventure with an engaging scenario.
""".strip()
        conversation = DM_SYSTEM_PROMPT.format(
            selected_genre=selected_genre,
            character_name=character_name,
            role=role
        ) + "\n\n"
        conversation += f"Setting: {selected_genre}\nPlayer Character: {character_name}, {role}\n\nDungeon Master: {initial}\n"
        ai_reply = get_ai_response(conversation, ollama_model)
        if ai_reply:
            print(f"Dungeon Master: {ai_reply}")
            speak(ai_reply)
            conversation += f"{ai_reply}"
            last_ai_reply = ai_reply

    while True:
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
            print(f"SFW mode {'ON' if censored else 'OFF'}.")
            continue

        if cmd == "/redo":
            if last_ai_reply:
                conversation = remove_last_ai_response(conversation)
                conversation += "\nDungeon Master:"
                ai_reply = get_ai_response(conversation, ollama_model)
                if ai_reply:
                    print(f"Dungeon Master: {ai_reply}")
                    speak(ai_reply)
                    conversation += f" {ai_reply}"
                    last_ai_reply = ai_reply
            else:
                print("Nothing to redo.")
            continue

        if cmd == "/save":
            with open("adventure.txt", "w", encoding="utf-8") as f:
                f.write(conversation)
            print("Adventure saved.")
            continue

        if cmd == "/load":
            if os.path.exists("adventure.txt"):
                with open("adventure.txt", "r", encoding="utf-8") as f:
                    conversation = f.read()
                print("Adventure loaded.")
            else:
                print("No saved adventure found.")
            continue

        if cmd == "/change":
            print("Available models:")
            for idx, m in enumerate(installed_models, 1):
                print(f"{idx}: {m}")
            while True:
                try:
                    new_idx = int(input("Enter number of new model: ").strip()) - 1
                    if 0 <= new_idx < len(installed_models):
                        ollama_model = installed_models[new_idx]
                        print(f"Model changed to: {ollama_model}")
                        break
                except:
                    print("Invalid selection.")
            continue

        # Regular player input
        conversation += f"\nPlayer: {user_input}\nDungeon Master:"
        ai_reply = get_ai_response(conversation, ollama_model)
        if ai_reply:
            print(f"Dungeon Master: {ai_reply}")
            speak(ai_reply)
            conversation += f" {ai_reply}"
            last_ai_reply = ai_reply

if __name__ == "__main__":
    main()

 
