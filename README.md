# Dungeo_ai
this is a dungeon ai run locally that use your llm 
Here's a **step-by-step tutorial** on how to install and run your Python-based local AI Dungeon Master application from GitHub on a local PC.

---

## 🧙‍♂️ Local AI Dungeon Master: Installation & Running Guide

This project lets you roleplay as a character in a richly described world with a local AI acting as your Dungeon Master. It uses:

* A local LLM (e.g., via `localhost:1234`)
* AllTalk TTS Server (`localhost:7851`)
* Python for runtime logic

---

### ✅ 1. Requirements

Make sure you have the following installed on your PC:

| Tool                 | Description                                                                                                                               |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **Python 3.9+**      | Main runtime                                                                                                                              |
| **pip**              | Python package installer                                                                                                                  |
| **Git**              | For downloading the repository                                                                                                            |
| **Local LLM server** | E.g., [Oobabooga Text Generation WebUI](https://github.com/oobabooga/text-generation-webui), [LM Studio](https://lmstudio.ai/), or Ollama |
| **AllTalk TTS**      | Local Text-to-Speech server [(https://github.com/WhyNotHugo/alltalk](https://github.com/erew123/alltalk_tts.git)](https://github.com/erew123/alltalk_tts)                              |

---

### 📁 2. Clone the Repository

Open a terminal and run:

```bash
git clone https://github.com/Laszlobeer/Dungeo_ai.git
cd Dungeo_ai
```

---

### 📦 3. Install Python Dependencies

Create a virtual environment (optional but recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

Install required packages:

```bash
pip install -r requirements.txt
```

If you don’t have a `requirements.txt`, create one with these contents:

```txt
requests
sounddevice
numpy
soundfile
```

Then install it:

```bash
pip install -r requirements.txt
```

---

### 🤖 4. Set Up Local AI Model

Run your LLM on `localhost:1234`. Options:

#### Option A: **Oobabooga WebUI**

* Download from: [https://github.com/oobabooga/text-generation-webui](https://github.com/oobabooga/text-generation-webui)
* Run the server and enable the `/v1/completions` API.
* Use a GGUF model or compatible format.

#### Option B: **LM Studio**

* Download from: [https://lmstudio.ai](https://lmstudio.ai)
* Choose a model and enable the OpenAI-compatible API.

---



### 🚀 6. Run the Game

Go back to the cloned project directory and run:

```bash
python dungeon ai.py
```

> Replace `dungeon ai.py` with whatever filename your script uses.

---

### 🔄 7. Save & Resume Adventures

The game supports:

* `/save`: Saves your session to `adventure.txt`
* `/load`: Restores it next time you run the program
* `/redo`: Re-rolls the last Dungeon Master response
* `/censored`: Toggles NSFW filtering

---

### 💡 Tips

* Make sure both the **AI model** and **TTS server** are running before you start the game.
* You can change the default character voice in the `speak()` function by editing the `voice` filename.
* If your LLM or TTS is on a different port or host, modify these lines:

```python
ALLTALK_API_URL = "http://localhost:7851/api/tts-generate"
# AI completion endpoint: inside get_ai_response()
"http://localhost:1234/v1/completions"
```

---

### ✅ Final Checklist

| Component                         | Status |
| --------------------------------- | ------ |
| Python 3.x                        | ✅      |
| Local AI LLM (`localhost:1234`)   | ✅      |
| AllTalk TTS (`localhost:7851`)    | ✅      |
| Script runs with `python main.py` | ✅      |

---

Let me know if you'd like a `README.md` or a `requirements.txt` auto-generated for your GitHub repo.
