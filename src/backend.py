import json
import os
import random
from flask import Flask, jsonify, render_template, request, session
from openai import OpenAI

client = OpenAI()

app = Flask(__name__)

app.secret_key = os.environ.get('FLASK_SECRET_KEY')

MODEL = "gpt-4o-mini"

QS = {}

TOPIC = ""

QS_NO = 4

RETRIES = 3

def get_questions(topic):
    with open("data/questions.json", "r") as q:
        questions: list[str] = json.loads(q.read())["topics"][topic]
        for _ in range(QS_NO):
            rnd = random.randint(0, len(questions) - 1)
            if rnd not in QS:
                QS[rnd] = questions[rnd]
            else:
                rnd = random.randint(0, len(questions) - 1) 
                QS[rnd] = questions[rnd]  
        

def evaluation(questions_answers):
    sys_msg = """
    You will evaulate the answers for the provided questions and only output a score of 0-10 for each one.
    Where 0 means it didn't answer the question correctly or is unrelated to question and 10 means it answered very well.
    Return the output as a json where the key is the index of the question and the value is the score.
    Do NOT return any other information or the questions. 
    You have to evaluate the meaning of the answers not the text similarity.
    """
    prompt = f"""
    Given the following Topic: {TOPIC} evulate each answer for each question: {questions_answers}.
    """

    response = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "system", "content": f"{sys_msg}"}, {"role": "user", "content": f"{prompt}"}],
    temperature=0.7)
    return response.choices[0].message.content.strip()


@app.route('/')
def home():
    session.pop('submitted', None)
    return render_template('index.html')

@app.route('/api/questions', methods=['POST'])
def generate_questions():
    global TOPIC
    global QS

    QS = {}
    TOPIC = ""

    TOPIC = request.json.get('text', '')

    get_questions(TOPIC)

    return jsonify({"generated_questions": [x for x in QS.values()]})


@app.route('/api/evaluation', methods=['POST'])
def generate_evaluation():
    answers: str = request.json.get('text', '')

    answers = answers.split("\n")

    hm = {}
    for q, a in zip(QS.values(), answers):
        hm[q] = a

    if session.get('submitted', False): 
        return jsonify({"score": 0, "msg": "You have already submitted the form. Please refresh the page to try again."})

    session['submitted'] = True
    for attempt in range(RETRIES):
        try:
            scores: dict = json.loads(evaluation(hm))
            tot_score = sum(scores.values())

            if tot_score < 30:
                msg = "You Are Trash. Go be an Uber Driver and make more money!"
            else:
                msg = "Nice one. Top lad! Now wait 5 weeks until we return with a lowball offer."

            return jsonify({"score": tot_score, "msg": msg})
            
        except Exception:
            if attempt < RETRIES - 1:
                print("Retrying...")  
            else:
                return jsonify({"score": 0, "msg": "Didn't work refresh and try again"})      


if __name__ == '__main__':
    app.run(debug=True)
