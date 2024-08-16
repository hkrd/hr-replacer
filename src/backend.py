import json
import os
import random
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
from openai import OpenAI

client = OpenAI()

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=os.environ.get('SESSION_SECRET_KEY'))


base_dir = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(base_dir, "templates"))

MODEL = "gpt-4o-mini"

QS = {}
TOPIC = ""
QS_NO = 4
RETRIES = 3


def get_questions(topic: str):
    with open("data/questions.json", "r") as q:
        questions: list[str] = json.loads(q.read())["topics"][topic]
        for _ in range(QS_NO):
            rnd = random.randint(0, len(questions) - 1)
            if rnd not in QS:
                QS[rnd] = questions[rnd]
            else:
                rnd = random.randint(0, len(questions) - 1)
                QS[rnd] = questions[rnd]


def evaluation(questions_answers: dict):
    sys_msg = """
    You will evaluate the answers for the provided questions and only output a score of 0-10 for each one.
    Where 0 means it didn't answer the question well or is unrelated and 10 means it answered it very well.
    Return the output as a json where the key is the index of the question and the value is the score.
    Do NOT return any other information or the questions. 
    You have to evaluate the meaning of the answers, not the text similarity.
    """
    prompt = f"""
    Given the following Topic: {TOPIC}, evaluate each answer for each question: {questions_answers}.
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    request.session.clear()
    return templates.TemplateResponse("index.html", {"request": request})


class QuestionRequest(BaseModel):
    text: str


@app.post("/api/questions", response_class=JSONResponse)
async def generate_questions(request: Request, question_request: QuestionRequest):
    global TOPIC, QS

    QS = {}
    TOPIC = question_request.text

    get_questions(TOPIC)

    return JSONResponse({"generated_questions": [x for x in QS.values()]})


class EvaluationRequest(BaseModel):
    text: list[str]


@app.post("/api/evaluation", response_class=JSONResponse)
async def generate_evaluation(request: Request, evaluation_request: EvaluationRequest):
    answers = evaluation_request.text

    hm = {q: a for q, a in zip(QS.values(), answers)}

    if request.session.get('submitted', False):
        return JSONResponse({"score": 0, "msg": "You have already submitted the form. Please refresh the page to try again."})

    request.session['submitted'] = True

    for attempt in range(RETRIES):
        try:
            scores: dict = json.loads(evaluation(hm))
            tot_score = sum(scores.values())

            if tot_score < 30:
                msg = "You Are Trash. Go be an Uber Driver and make more money!"
            else:
                msg = "Nice one. Top lad! Now wait 5 weeks until we return with a lowball offer."

            return JSONResponse({"score": tot_score, "msg": msg})

        except Exception as e:
            print(e)
            if attempt < RETRIES - 1:
                print("Retrying...")
            else:
                return JSONResponse({"score": 0, "msg": "Didn't work refresh and try again"})


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
