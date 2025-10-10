# app.py
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from patient_history_chatbot import RAGChatbot

# Minimal Flask setup for demo
app = Flask(__name__)
app.secret_key = "dev-demo-key"  # Needed for session; fine for a demo

# Create one bot instance per session (kept simple with a global + session guard)
# For a real multi-user app, you'd persist per-user state differently.
bot_instances = {}


def get_bot():
    """Get or create the user's bot instance tied to their session."""
    sid = session.get("sid")
    if not sid:
        sid = request.headers.get("X-Session-Id") or request.remote_addr or "anon"
        session["sid"] = sid
    if sid not in bot_instances:
        bot_instances[sid] = RAGChatbot()
    return bot_instances[sid]


@app.route("/", methods=["GET"])
def index():
    """
    Render the chat UI. Patient ID is required to start chat with RAG.
    The HTML will handle inputs for patient_id and the message field.
    """
    return render_template("index.html")


@app.route("/set_patient", methods=["POST"])
def set_patient():
    """
    Set the patient ID on the bot. Expected form fields:
    - patient_id: integer-like string
    """
    patient_id = request.form.get("patient_id", "").strip()
    if not patient_id.isdigit():
        return jsonify({"ok": False, "error": "Please enter a valid numeric patient ID."}), 400

    bot = get_bot()
    bot.set_patient_id(int(patient_id))
    session["patient_id"] = int(patient_id)
    return jsonify({"ok": True, "message": f"Patient set to {patient_id}"})


@app.route("/chat", methods=["POST"])
def chat():
    """
    Handle a single chat turn. Expected form fields:
    - message: user prompt
    - do_search: optional ("true"/"false") to enable RAG search
    Uses the patient_id saved in session for RAG.
    """
    user_message = request.form.get("message", "").strip()
    do_search_raw = request.form.get("do_search", "true").strip().lower()
    do_search = do_search_raw in ("true", "1", "yes")

    if not user_message:
        return jsonify({"ok": False, "error": "Message cannot be empty."}), 400

    bot = get_bot()

    # If do_search is requested, ensure patient_id is present
    if do_search:
        patient_id = session.get("patient_id", 0)
        if not patient_id:
            return jsonify({"ok": False, "error": "Set patient ID before chatting with RAG search."}), 400
        # Make sure bot has the same patient_id as session
        bot.set_patient_id(int(patient_id))

    try:
        reply = bot.run(user_message, do_search=do_search)
    except ValueError as e:
        # Handles the "Patient ID is not set" case from the bot
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        # Minimal demo handling
        return jsonify({"ok": False, "error": f"Chat error: {e}"}), 500

    return jsonify({"ok": True, "reply": reply})


@app.route("/reset", methods=["POST"])
def reset():
    """
    Reset the conversation memory for the current session's bot.
    Keeps the patient_id unless the client asks to clear it via query/form.
    Optional form field:
    - clear_patient: "true" to also clear patient_id
    """
    bot = get_bot()
    bot.reset()

    clear_patient_raw = request.form.get("clear_patient", "false").strip().lower()
    if clear_patient_raw in ("true", "1", "yes"):
        session.pop("patient_id", None)

    return jsonify({"ok": True, "message": "Chat reset."})


if __name__ == "__main__":
    # Run the Flask app for demo
    app.run(host="0.0.0.0", port=5000, debug=True)