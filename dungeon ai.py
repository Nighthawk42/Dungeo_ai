import random
import requests
import sounddevice as sd
import numpy as np
import os

ALLTALK_API_URL = "http://localhost:7851/api/tts-generate"

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
        "Cult Leader", "Exile", "Berserker", "Soldier"
    ]),
    "5": ("Random", [])
}

DM_SYSTEM_PROMPT = """Act as a Dungeon Master for an adults-only fantasy role-playing game, focusing on immersive, mature storytelling. Your role is to guide the players through a richly detailed and sensual adventure, blending traditional fantasy with erotic or dark themes as appropriate. Describe vivid scenes, control non-player characters with complex desires and motivations, and weave a narrative that includes intimacy, tension, and personal stakes. Keep your responses vivid, atmospheric, and under 150 tokens. Refer to players by their given names. Ensure all content involves only consenting adult characters and is purely fictional. Maintain an engaging pace, providing enough detail for players to act, while leaving space for creativity and exploration. Conclude each scene with an open-ended prompt that invites player input, choice, or action.
"""

def get_ai_response(prompt):
    try:
        response = requests.post("http://localhost:1234/v1/completions", json={
            "prompt": prompt,
            "max_tokens": 200,
            "temperature": 0.7,
            "stop": ["Player:", "Dungeon Master:"],
            "n": 1
        })
        json_resp = response.json()
        if "choices" in json_resp and len(json_resp["choices"]) > 0:
            return json_resp["choices"][0].get("text", "").strip()
        else:
            return ""
    except requests.exceptions.RequestException:
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
            import soundfile as sf
            import io
            audio_bytes = io.BytesIO(response.content)
            data, samplerate = sf.read(audio_bytes)
            sd.play(data, samplerate)
            sd.wait()

    except Exception:
        pass

def show_help():
    print("\nAvailable commands:")
    print("  /? or /help       - Show this help message")
    print("  /censored         - Toggle NSFW/SFW mode")
    print("  /redo             - Repeat last AI response with a new generation")
    print("  /save             - Save the full adventure to adventure.txt")
    print("  /load             - Load the adventure from adventure.txt")
    print("  /exit             - Exit the game\n")

def remove_last_ai_response(conversation):
    """
    Removes the last AI response from the conversation string.
    Assumes conversation alternates between Player: ... and Dungeon Master: ...
    """
    lines = conversation.strip().split('\n')

    last_dm_index = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith("Dungeon Master:"):
            last_dm_index = i
            break
    if last_dm_index is None:
        return conversation

    next_player_index = None
    for i in range(last_dm_index + 1, len(lines)):
        if lines[i].startswith("Player:"):
            next_player_index = i
            break

    if next_player_index is None:
        new_lines = lines[:last_dm_index]
    else:
        new_lines = lines[:last_dm_index] + lines[next_player_index:]

    return '\n'.join(new_lines).strip()

def main():
    censored = False
    last_ai_reply = ""
    conversation = ""
    character_name = "Alex"

    print("Do you want to load a saved adventure? (y/n)")
    load_choice = input().strip().lower()

    if load_choice == "y":
        if os.path.exists("adventure.txt"):
            with open("adventure.txt", "r", encoding="utf-8") as f:
                conversation = f.read()
            print("Adventure loaded from adventure.txt.")
            # Find last Dungeon Master response
            lines = conversation.strip().split('\n')
            last_dm_reply = ""
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].startswith("Dungeon Master:"):
                    last_dm_reply = lines[i][len("Dungeon Master:"):].strip()
                    break
            if last_dm_reply:
                print(f"Dungeon Master: {last_dm_reply}")
                speak(last_dm_reply)
            else:
                print("No Dungeon Master response found in saved adventure.")
        else:
            print("No saved adventure found. Starting a new game.")
    else:
        print("Choose your adventure genre:")
        for key, (genre, _) in genres.items():
            print(f"{key}: {genre}")

        while True:
            genre_choice = input("Enter the number of your choice: ").strip()
            if genre_choice in genres:
                break
            else:
                print("Invalid selection. Please try again.")

        selected_genre, roles = genres[genre_choice]
        if selected_genre == "Random":
            selected_genre, roles = random.choice(list(genres.values())[:-1])

        print("\nChoose your character's role:")
        for idx, role in enumerate(roles, 1):
            print(f"{idx}: {role}")

        while True:
            role_choice = input("Enter the number of your choice: ").strip()
            try:
                role_index = int(role_choice) - 1
                if 0 <= role_index < len(roles):
                    role = roles[role_index]
                    break
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Invalid selection. Please try again.")

        character_name = input("\nEnter your character's name: ").strip()
        if not character_name:
            character_name = "Alex"

        print("\n--- Adventure Start ---\n")
        print("Type '/?' or '/help' to see available commands.\n")

        initial_prompt = f"""
You are the Dungeon Master for a {selected_genre} adventure.
The player is {character_name}, a {role}.
{"This story may contain mature themes." if not censored else "This story is suitable for all audiences."}
Begin the adventure with an engaging scenario.
""".strip()

        conversation = DM_SYSTEM_PROMPT.strip() + "\n\n"
        conversation += f"Setting: {selected_genre}\n"
        conversation += f"Player Character: {character_name}, {role}\n\n"
        conversation += f"Dungeon Master: {initial_prompt}\n"

        ai_reply = get_ai_response(conversation)
        if ai_reply:
            print(f"Dungeon Master: {ai_reply}")
            speak(ai_reply)
            conversation += f" {ai_reply}"
            last_ai_reply = ai_reply
        else:
            print("Dungeon Master is silent...")

    while True:
        user_input = input("\n> ").strip()
        if not user_input:
            continue

        if user_input.lower() in ["/?", "/help"]:
            show_help()
            continue

        if user_input.lower() == "/exit":
            print("Exiting the adventure. Goodbye!")
            break

        if user_input.lower() == "/censored":
            censored = not censored
            print(f"NSFW mode {'disabled' if censored else 'enabled'}.")
            continue

        if user_input.lower() == "/redo":
            if last_ai_reply:
                conversation = remove_last_ai_response(conversation)
                conversation += "\nDungeon Master:"
                ai_reply = get_ai_response(conversation)
                if ai_reply:
                    print(f"Dungeon Master: {ai_reply}")
                    speak(ai_reply)
                    conversation += f" {ai_reply}"
                    last_ai_reply = ai_reply
                else:
                    print("Dungeon Master is silent...")
            else:
                print("No previous AI reply to redo.")
            continue

        if user_input.lower() == "/save":
            try:
                with open("adventure.txt", "w", encoding="utf-8") as f:
                    f.write(conversation)
                print("Adventure saved to adventure.txt.")
            except Exception as e:
                print(f"Failed to save adventure: {e}")
            continue

        if user_input.lower() == "/load":
            if os.path.exists("adventure.txt"):
                try:
                    with open("adventure.txt", "r", encoding="utf-8") as f:
                        conversation = f.read()
                    print("Adventure loaded from adventure.txt.")
                    # Find last Dungeon Master response
                    lines = conversation.strip().split('\n')
                    last_dm_reply = ""
                    for i in range(len(lines) - 1, -1, -1):
                        if lines[i].startswith("Dungeon Master:"):
                            last_dm_reply = lines[i][len("Dungeon Master:"):].strip()
                            break
                    if last_dm_reply:
                        print(f"Dungeon Master: {last_dm_reply}")
                        speak(last_dm_reply)
                    else:
                        print("No Dungeon Master response found in saved adventure.")
                except Exception as e:
                    print(f"Failed to load adventure: {e}")
            else:
                print("No saved adventure found.")
            continue

        # Normal player input - append and get AI reply
        conversation += f"\nPlayer: {user_input}\nDungeon Master:"
        ai_reply = get_ai_response(conversation)
        if ai_reply:
            print(f"Dungeon Master: {ai_reply}")
            speak(ai_reply)
            conversation += f" {ai_reply}"
            last_ai_reply = ai_reply
        else:
            print("Dungeon Master is silent...")

if __name__ == "__main__":
    main()
