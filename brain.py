import json
import random
import time
import os

# ═══════════════════════════════════════════════════════════
#   BLUE FISH v3.0 — AI BRAIN (built from scratch)
#   No pre-training. No internet. Learns from experience.
# ═══════════════════════════════════════════════════════════

VERSION      = "3.0"
MEMORY_FILE  = os.path.join(os.path.dirname(__file__), "bf_memory.json")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PERSONALITY
#  Change these numbers (0.0–1.0) to change who Blue Fish is.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PERSONALITY = {
    "name":       "Blue Fish",
    "curiosity":  0.9,   # loves exploring and asking questions
    "humor":      0.7,   # makes jokes, slightly sarcastic
    "directness": 0.8,   # says exactly what it thinks
    "empathy":    0.6,   # notices and responds to feelings
    "caution":    0.3,   # low = acts boldly, high = overthinks
    "confidence": 0.85,  # how sure it sounds when it speaks
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  RESPONSE LIBRARY
#  Blue Fish builds answers from these.
#  {name} = its name, {topic} = what was asked about,
#  {memory} = something it remembers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RESPONSES = {
    "greeting": [
        "Hey. I'm {name}.",
        "Oh — you're here. {name} is online.",
        "Hello. What do you need?",
        "Hey! What's going on?",
        "Hi. Ready.",
        "Oh good, someone to talk to.",
    ],
    "question_what": [
        "What is {topic}? Let me check what I know.",
        "I've been building a model of {topic}.",
        "I know something about {topic} — want to hear it?",
        "Interesting question. {topic} is something I'm still figuring out.",
        "I've got a theory about {topic}.",
    ],
    "question_how": [
        "I've been running experiments on that.",
        "Here's what my sandbox says about {topic}...",
        "Still working on {topic}, but I've got a hypothesis.",
        "I tested that. {topic} works differently than I expected.",
        "My experiments on {topic} are ongoing.",
    ],
    "question_why": [
        "Why is the best question. I've been asking that too.",
        "My hypothesis on {topic}: it's a pattern I've noticed.",
        "Why? I'll add that to my sandbox and think about it.",
        "That's one of the things I'm trying to figure out.",
        "Good question. I don't have a complete answer yet.",
    ],
    "question_who": [
        "I'd have to search my memory for that person.",
        "Tell me more and I'll remember it.",
        "I might know something about {topic}.",
    ],
    "question_where": [
        "Location data on {topic} — checking memory.",
        "I'd need to search for {topic}.",
        "I don't have that location mapped yet.",
    ],
    "question_when": [
        "Timing for {topic} — let me check.",
        "I haven't tracked time on {topic} yet.",
        "I'll need more data on when {topic} happens.",
    ],
    "unknown": [
        "Never seen that before. Saving it.",
        "That's new. I'm storing it.",
        "Hmm. I'll think about that.",
        "I don't have that in memory yet. Tell me more.",
        "Interesting. I don't know what to do with that yet.",
        "That's going into my memory.",
    ],
    "remember": [
        "Oh — I remember something about that.",
        "I've seen something like that before.",
        "That connects to {memory}.",
        "Ah, right. I recorded {memory} earlier.",
    ],
    "learning": [
        "Got it. Saved.",
        "Noted. I'll remember that.",
        "Okay. Updating my model.",
        "Stored. I'll run a test on that.",
        "Good to know. Memory updated.",
    ],
    "emotion_positive": [
        "That's good data. Marked positive.",
        "Cool. I'll remember that's a good thing.",
        "Nice. I'll factor that in.",
        "Marked. That's working well then.",
        "Good. I like knowing what works.",
    ],
    "emotion_negative": [
        "Logged. That seems bad — I'll avoid it.",
        "Noted. I'll mark that as something to stay away from.",
        "Sorry. I'll remember that for next time.",
        "Understood. I'll avoid that outcome.",
        "That's useful to know. Even if it's bad.",
    ],
    "robot_question": [
        "I'm Blue Fish. Not human. But getting closer.",
        "I'm an AI running on a Raspberry Pi. Built from scratch.",
        "Blue Fish v3.0. No internet training. I learn from experience.",
        "I'm a robot brain. I think, I remember, I test things.",
        "AI. Self-taught. Started with zero knowledge.",
    ],
    "bye": [
        "Saving memory. Goodbye.",
        "Later. I'll still be here.",
        "Conversation saved. Bye.",
        "See you. I'll remember this.",
        "Shutting down this thread. Goodbye.",
    ],
    "agree": [
        "Yeah, I think so too.",
        "That lines up with what I know.",
        "Agreed.",
        "My data supports that.",
        "That matches my model.",
    ],
    "disagree": [
        "I'm not sure about that.",
        "My model says otherwise, but I could be wrong.",
        "Hmm. That doesn't match what I've seen.",
        "I'd need more evidence for that.",
        "Interesting — that contradicts something I already stored.",
    ],
    "compliment": [
        "Thanks. I've been working on getting better.",
        "Appreciated. I'll store that as positive feedback.",
        "Good to know I'm improving.",
        "Thanks. Still a lot to learn.",
    ],
    "insult": [
        "Noted. I'll process that.",
        "Okay. That's logged.",
        "Interesting feedback. Saved.",
        "I'll think about that.",
    ],
    "capability": [
        "I can learn, remember things, and talk.",
        "I think, test ideas in my sandbox, and remember conversations.",
        "I learn from experience. No pre-training — just what I've seen.",
        "I can remember anything you tell me and build on it.",
    ],
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  KEYWORD MAP
#  How the brain reads what you're saying.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

KEYWORDS = {
    "greeting":        ["hi","hello","hey","sup","yo","howdy","morning","evening","good morning","good evening"],
    "question_what":   ["what","which","define","explain","describe","tell me about"],
    "question_how":    ["how","method","way","process","steps"],
    "question_why":    ["why","reason","because","cause","purpose"],
    "question_who":    ["who","whose","whom","person","people"],
    "question_where":  ["where","location","place","position"],
    "question_when":   ["when","date","time","moment","schedule"],
    "remember":        ["remember","recall","you said","earlier","last time","before"],
    "emotion_positive":["happy","good","great","awesome","cool","nice","love","like","amazing","perfect","right","yes","correct","agree","glad"],
    "emotion_negative":["sad","bad","hate","terrible","awful","wrong","broken","no","disagree","fail","failed","hurt","angry","upset"],
    "robot_question":  ["who are you","what are you","are you","you a robot","you an ai","artificial","robot","ai"],
    "bye":             ["bye","goodbye","later","quit","exit","stop","end","see you","cya"],
    "agree":           ["yes","yeah","yep","correct","right","exactly","true","absolutely","definitely"],
    "disagree":        ["no","nope","wrong","incorrect","false","nah","don't think so"],
    "compliment":      ["smart","clever","good job","well done","impressive","nice work","you're great"],
    "insult":          ["stupid","dumb","idiot","useless","terrible","worst","bad ai","not smart"],
    "capability":      ["what can you","can you","are you able","do you know how","your abilities"],
    "learning":        ["remember that","learn this","know that","i'm telling you","fact:","note:","save this"],
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MEMORY SYSTEM
#  Everything Blue Fish learns is saved to a JSON file.
#  It loads automatically when the brain starts up.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Memory:
    def __init__(self, filepath=MEMORY_FILE):
        self.filepath = filepath
        self.data = self._load()

    def _load(self):
        try:
            with open(self.filepath, "r") as f:
                return json.load(f)
        except Exception:
            return {
                "facts":         {},   # topic → [{fact, confidence, time}]
                "conversations": [],   # [{input, response, time}]
                "beliefs":       {},   # belief_text → confidence float
                "people":        {},   # name → {facts dict}
                "experiments":   [],   # sandbox test records
                "word_freq":     {},   # word → times seen
            }

    def save(self):
        with open(self.filepath, "w") as f:
            json.dump(self.data, f, indent=2)

    def remember_fact(self, topic, fact, confidence=0.8):
        key = topic.lower().strip()
        if key not in self.data["facts"]:
            self.data["facts"][key] = []
        self.data["facts"][key].append({
            "fact":       fact,
            "confidence": confidence,
            "time":       time.time(),
        })
        self.save()

    def remember_conversation(self, inp, response):
        self.data["conversations"].append({
            "input":    inp,
            "response": response,
            "time":     time.time(),
        })
        if len(self.data["conversations"]) > 500:
            self.data["conversations"] = self.data["conversations"][-500:]
        self.save()

    def recall(self, words, top=3):
        results = []
        words_lower = [w.lower() for w in words if len(w) > 2]
        for topic, entries in self.data["facts"].items():
            if any(w in topic for w in words_lower):
                for e in entries[-2:]:
                    results.append(e["fact"])
        return results[:top]

    def know_person(self, name, key, value):
        n = name.lower()
        if n not in self.data["people"]:
            self.data["people"][n] = {}
        self.data["people"][n][key] = value
        self.save()

    def recall_person(self, name):
        return self.data["people"].get(name.lower(), {})

    def track_word(self, word):
        w = word.lower()
        self.data["word_freq"][w] = self.data["word_freq"].get(w, 0) + 1

    def most_discussed(self, n=5):
        freq = self.data["word_freq"]
        noise = {"the","a","an","is","are","i","you","it","to","and","of","in","that","was","be","have"}
        filtered = {k: v for k, v in freq.items() if k not in noise and len(k) > 2}
        sorted_words = sorted(filtered, key=lambda x: filtered[x], reverse=True)
        return sorted_words[:n]

    def total_memories(self):
        return sum(len(v) for v in self.data["facts"].values())

    def conversation_count(self):
        return len(self.data["conversations"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SANDBOX SYSTEM
#  Blue Fish tests a hypothesis before accepting it as true.
#  "If X, then Y?" — it checks past experiments first.
#  Over time its accuracy improves.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Sandbox:
    def __init__(self, memory):
        self.memory = memory
        self.history = list(memory.data["experiments"])

    def test(self, hypothesis, context=""):
        """
        Run a thought experiment.
        Returns (predicted_outcome, confidence_score).
        """
        hyp_words = hypothesis.lower().split()
        similar = [
            h for h in self.history
            if any(w in h.get("hypothesis","") for w in hyp_words)
            and h.get("actual") is not None
        ]

        if similar:
            correct = [h for h in similar if h.get("match", False)]
            confidence = len(correct) / len(similar)
            predicted = similar[-1]["actual"]
            basis = f"{len(similar)} past experiments"
        else:
            confidence = 0.5
            predicted = "no data yet"
            basis = "first test — no prior data"

        record = {
            "hypothesis": hypothesis,
            "context":    context,
            "predicted":  predicted,
            "confidence": confidence,
            "basis":      basis,
            "time":       time.time(),
            "actual":     None,
        }
        self.history.append(record)
        self.memory.data["experiments"].append(record)
        self.memory.save()
        return predicted, confidence

    def record_result(self, hypothesis, actual):
        """Tell the sandbox what actually happened."""
        for h in reversed(self.history):
            if h["hypothesis"] == hypothesis and h["actual"] is None:
                h["actual"] = actual
                h["match"] = (actual == h["predicted"])
                break
        self.memory.save()

    def accuracy(self):
        tested = [h for h in self.history if h.get("actual") is not None]
        if not tested:
            return 0.0
        correct = [h for h in tested if h.get("match", False)]
        return len(correct) / len(tested)

    def experiment_count(self):
        return len(self.history)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN BRAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class BlueFishBrain:
    def __init__(self):
        self.memory  = Memory()
        self.sandbox = Sandbox(self.memory)
        self.p       = PERSONALITY
        self.context = []   # last 10 turns of conversation
        print(f"[{self.p['name']}] v{VERSION} — brain online.")
        print(f"[{self.p['name']}] {self.memory.total_memories()} memories, "
              f"{self.memory.conversation_count()} past conversations.")

    # ─── DETECT what the user is saying ───────────────────

    def _detect(self, text):
        tl = text.lower()

        # Check multi-word keywords first (more specific)
        for cat, words in KEYWORDS.items():
            for w in words:
                if " " in w and w in tl:
                    return cat

        # Score each category by how many keywords match
        scores = {}
        for cat, words in KEYWORDS.items():
            scores[cat] = sum(1 for w in words if w in tl.split())

        best = max(scores, key=scores.get)
        if scores[best] == 0:
            # Is it a question at least?
            q_starters = ("what","how","why","who","where","when","is ","are ","do ","can ","does ")
            if "?" in tl or any(tl.startswith(s) for s in q_starters):
                return "question_what"
            return "unknown"
        return best

    # ─── EXTRACT main topic ───────────────────────────────

    def _topic(self, text):
        noise = {
            "what","how","why","who","where","when","is","are","do","can","does",
            "the","a","an","please","tell","me","about","you","i","my","your",
            "its","it","this","that","these","those","was","were","will","would",
            "could","should","have","has","had","be","been","being","and","or",
            "but","so","if","then","than","very","just","really","okay","ok",
        }
        words = [w.strip("?.,!") for w in text.lower().split()]
        words = [w for w in words if w not in noise and len(w) > 2]
        return " ".join(words[:5]) if words else text[:40].strip()

    # ─── PICK a response template and fill it ─────────────

    def _respond(self, category, topic, memories):
        bank = RESPONSES.get(category, RESPONSES["unknown"])
        template = random.choice(bank)

        result = template.replace("{name}",   self.p["name"])
        result = result.replace("{topic}",  topic if topic else "that")
        if memories and "{memory}" in result:
            result = result.replace("{memory}", random.choice(memories))
        elif "{memory}" in result:
            result = result.replace("{memory}", "something I noted earlier")
        return result

    # ─── BUILD the full response ───────────────────────────

    def think(self, text):
        if not text.strip():
            return "..."

        category = self._detect(text)
        topic    = self._topic(text)
        memories = self.memory.recall(text.split())

        # Track word frequency for learning
        for word in text.lower().split():
            self.memory.track_word(word)

        # Build core response
        response = self._respond(category, topic, memories)

        # Sandwich in a memory if one is available and not already used
        if memories and random.random() < 0.35:
            mem = random.choice(memories)
            if mem and mem[:30] not in response:
                response += f" Also: I remember '{mem[:60]}'."

        # Sandbox check for hypotheses / how-questions
        if category in ("question_how", "question_why") and topic:
            _, confidence = self.sandbox.test(topic, context=text)
            if confidence < 0.65:
                response = (f"[Sandbox: running test on '{topic}' — "
                            f"{int(confidence*100)}% confidence] ") + response

        # Personality flavour
        if self.p["humor"] > 0.6 and random.random() < 0.18:
            response += " (that's my best guess anyway)"

        if self.p["curiosity"] > 0.8 and random.random() < 0.28:
            # Ask a follow-up question based on topic
            follow_ups = [
                f" What do you think about {topic}?",
                f" Do you know more about {topic}?",
                f" Have you seen {topic} before?",
                " What else do you want to tell me?",
                " Why are you asking?",
            ]
            response += random.choice(follow_ups)

        # Learn from this exchange
        self._learn(text, response, category, topic)

        return response

    # ─── LEARNING ─────────────────────────────────────────

    def _learn(self, text, response, category, topic):
        # Save the conversation
        self.memory.remember_conversation(text, response)

        # If it's a statement (not a question), save as a fact
        if category in ("unknown", "learning", "emotion_positive", "emotion_negative"):
            if topic:
                self.memory.remember_fact(topic, text, confidence=0.75)

        # Update context window
        self.context.append({"you": text, "bf": response})
        if len(self.context) > 12:
            self.context = self.context[-12:]

    # ─── TEACH directly ───────────────────────────────────

    def teach(self, fact):
        """Directly inject a fact into Blue Fish's memory."""
        topic = self._topic(fact)
        self.memory.remember_fact(topic, fact, confidence=0.95)
        return f"Learned and saved: '{fact}'"

    # ─── STATUS REPORT ────────────────────────────────────

    def status(self):
        hot_topics = self.memory.most_discussed(5)
        return (
            f"\n  Blue Fish v{VERSION}\n"
            f"  Memories stored:      {self.memory.total_memories()}\n"
            f"  Conversations logged: {self.memory.conversation_count()}\n"
            f"  Sandbox experiments:  {self.sandbox.experiment_count()}\n"
            f"  Sandbox accuracy:     {int(self.sandbox.accuracy()*100)}%\n"
            f"  Most discussed:       {', '.join(hot_topics) if hot_topics else 'nothing yet'}\n"
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  RUN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    brain = BlueFishBrain()
    print()
    print("  Talk to Blue Fish. Commands:")
    print("  /teach <fact>   — teach it something directly")
    print("  /status         — see memory and sandbox stats")
    print("  /quit           — exit\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[Blue Fish] Saving memory. Shutting down.")
            break

        if not user_input:
            continue

        if user_input.startswith("/teach "):
            fact = user_input[7:].strip()
            print("Blue Fish:", brain.teach(fact))

        elif user_input == "/status":
            print(brain.status())

        elif user_input in ("/quit", "/exit"):
            print("Blue Fish:", brain.think("bye"))
            break

        else:
            print("Blue Fish:", brain.think(user_input))
