from dotenv import load_dotenv
load_dotenv()

from functools import wraps
from flask import Flask, jsonify, Response, request, redirect, url_for
import flask
import os
from cache import MemoryCache
import db
from flasgger import Swagger

app = Flask(__name__, static_url_path='')
swagger = Swagger(app)

# SETUP
cache = MemoryCache()

# from vanna.local import LocalContext_OpenAI
# vn = LocalContext_OpenAI()

from vanna.remote import VannaDefault
vn = VannaDefault(model=os.environ['VANNA_MODEL'], api_key=os.environ['VANNA_API_KEY'])

db.connect(vn=vn)

# NO NEED TO CHANGE ANYTHING BELOW THIS LINE
def requires_cache(fields):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            id = request.args.get('id')

            if id is None:
                return jsonify({"type": "error", "error": "No id provided"})
            
            for field in fields:
                if cache.get(id=id, field=field) is None:
                    return jsonify({"type": "error", "error": f"No {field} found"})
            
            field_values = {field: cache.get(id=id, field=field) for field in fields}
            
            # Add the id to the field_values
            field_values['id'] = id

            return f(*args, **field_values, **kwargs)
        return decorated
    return decorator

@app.route('/api/v0/generate_questions', methods=['GET'])
def generate_questions():
    """
    Generate a list of questions that can be asked based on the current context.
    ---
    responses:
      200:
        description: A list of questions that can be asked.
        schema:
          type: object
          properties:
            type:
              type: string
              example: question_list
            questions:
              type: array
              items:
                type: string
              example: ["What is the average salary?", "How many employees are there?"]
    """
    return jsonify({
        "type": "question_list", 
        "questions": vn.generate_questions(),
        "header": "Here are some questions you can ask:"
        })

@app.route('/api/v0/generate_sql', methods=['GET'])
def generate_sql():
    """
    Generate SQL based on the question provided.
    ---
    parameters:
        - name: question
          in: query
          type: string
          required: true
          description: The question to generate SQL for.
    responses:
        200:
            description: The generated SQL.
            schema:
            type: object
            properties:
                type:
                type: string
                example: sql
                id:
                type: string
                example: 12345
                text:
                type: string
                example: SELECT * FROM employees WHERE salary > 50000
    """
    question = flask.request.args.get('question')

    if question is None:
        return jsonify({"type": "error", "error": "No question provided"})

    id = cache.generate_id(question=question)
    sql = vn.generate_sql(question=question)

    cache.set(id=id, field='question', value=question)
    cache.set(id=id, field='sql', value=sql)

    return jsonify(
        {
            "type": "sql", 
            "id": id,
            "text": sql,
        })

@app.route('/api/v0/run_sql', methods=['GET'])
@requires_cache(['sql'])
def run_sql(id: str, sql: str):
    """
    Run the SQL query and return the results.
    ---
    parameters:
        - name: id
          type: string
          required: true
          description: The ID of the SQL query to run.
    responses:
        200:
            description: The results of the SQL query.
            schema:
                type: object
                properties:
                    type:
                        type: string
                        example: df
                    id:
                        type: string
                        example: 12345
                    df:
                        type: array
                        items:
                            type: object
                        example: [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
    """
    try:
        df = vn.run_sql(sql=sql)

        cache.set(id=id, field='df', value=df)

        return jsonify(
            {
                "type": "df", 
                "id": id,
                "df": df.head(10).to_json(orient='records'),
            })

    except Exception as e:
        return jsonify({"type": "error", "error": str(e)})

@app.route('/api/v0/download_csv', methods=['GET'])
@requires_cache(['df'])
def download_csv(id: str, df):
    """
    Download the DataFrame as a CSV file.
    ---
    parameters:
        - name: id
          type: string
          required: true
          description: The ID of the DataFrame to download.
    responses:
        200:
            description: The CSV file.
            schema:
                type: object
                properties:
                    type:
                        type: string
                        example: csv
                    id:
                        type: string
                        example: 12345
                    csv:
                        type: string
                        example: "name,age\nJohn,30\nJane,25"
    """
    csv = df.to_csv()

    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-disposition":
                 f"attachment; filename={id}.csv"})

@app.route('/api/v0/generate_plotly_figure', methods=['GET'])
@requires_cache(['df', 'question', 'sql'])
def generate_plotly_figure(id: str, df, question, sql):
    """
    Generate a Plotly figure based on the question and SQL query.
    ---
    parameters:
        - name: id
          type: string
          required: true
          description: The ID of the Plotly figure to generate.
    responses:
        200:
            description: The generated Plotly figure.
            schema:
                type: object
                properties:
                    type:
                        type: string
                        example: plotly_figure
                    id:
                        type: string
                        example: 12345
                    fig:
                        type: object
                        example: {"data": [{"x": [1, 2, 3], "y": [4, 5, 6]}]}
    """
    try:
        code = vn.generate_plotly_code(question=question, sql=sql, df_metadata=f"Running df.dtypes gives:\n {df.dtypes}")
        fig = vn.get_plotly_figure(plotly_code=code, df=df, dark_mode=False)
        fig_json = fig.to_json()

        cache.set(id=id, field='fig_json', value=fig_json)

        return jsonify(
            {
                "type": "plotly_figure", 
                "id": id,
                "fig": fig_json,
            })
    except Exception as e:
        # Print the stack trace
        import traceback
        traceback.print_exc()

        return jsonify({"type": "error", "error": str(e)})

@app.route('/api/v0/get_training_data', methods=['GET'])
def get_training_data():
    """
    Get the training data from the database.
    ---
    responses:
        200:
            description: The training data.
            schema:
                type: object
                properties:
                    type:
                        type: string
                        example: df
                    id:
                        type: string
                        example: training_data
                    df:
                        type: array
                        items:
                            type: object
                        example: [{"question": "What is the average salary?", "sql": "SELECT AVG(salary) FROM employees"}]
    """
    df = vn.get_training_data()

    return jsonify(
    {
        "type": "df", 
        "id": "training_data",
        "df": df.head(25).to_json(orient='records'),
    })

@app.route('/api/v0/remove_training_data', methods=['POST'])
def remove_training_data():
    """
    Remove training data from the database.
    ---
    parameters:
        - name: id
          in: body
          type: string
          required: true
          description: The ID of the training data to remove.
    responses:
        200:
            description: The result of the removal.
            schema:
                type: object
                properties:
                    success:
                        type: boolean
                        example: true
                    error:
                        type: string
                        example: "Couldn't remove training data"
    """
    # Get id from the JSON body
    id = flask.request.json.get('id')

    if id is None:
        return jsonify({"type": "error", "error": "No id provided"})

    if vn.remove_training_data(id=id):
        return jsonify({"success": True})
    else:
        return jsonify({"type": "error", "error": "Couldn't remove training data"})

@app.route('/api/v0/train', methods=['POST'])
def add_training_data():
    """
    Add training data to the database.
    ---
    parameters:
        - name: question
          in: body
          type: string
          required: true
          description: The question to add.
        - name: sql
          in: body
          type: string
          required: true
          description: The SQL query to add.
        - name: ddl
          in: body
          type: string
          required: true
          description: The DDL query to add.
        - name: documentation
          in: body
          type: string
          required: true
          description: The documentation to add.
    responses:
        200:
            description: The result of the training.
            schema:
                type: object
                properties:
                    id:
                        type: string
                        example: 12345
                    error:
                        type: string
                        example: Could not train the model
    """
    question = flask.request.json.get('question')
    sql = flask.request.json.get('sql')
    ddl = flask.request.json.get('ddl')
    documentation = flask.request.json.get('documentation')

    try:
        id = vn.train(question=question, sql=sql, ddl=ddl, documentation=documentation)

        return jsonify({"id": id})
    except Exception as e:
        print("TRAINING ERROR", e)
        return jsonify({"type": "error", "error": str(e)})

@app.route('/api/v0/generate_followup_questions', methods=['GET'])
@requires_cache(['df', 'question', 'sql'])
def generate_followup_questions(id: str, df, question, sql):
    """
    Generate followup questions based on the current question and SQL query.
    ---
    parameters:
        - name: id
          in: query
          type: string
          required: true
          description: The ID of the followup questions to generate.
    responses:
        200:
            description: The generated followup questions.
            schema:
                type: object
                properties:
                    type:
                        type: string
                        example: question_list
                    id:
                        type: string
                        example: 12345
                    questions:
                        type: array
                        items:
                            type: string
                        example: ["What is the average salary?", "How many employees are there?"]
    """
    followup_questions = vn.generate_followup_questions(question=question, sql=sql, df=df)

    cache.set(id=id, field='followup_questions', value=followup_questions)

    return jsonify(
        {
            "type": "question_list", 
            "id": id,
            "questions": followup_questions,
            "header": "Here are some followup questions you can ask:"
        })

@app.route('/api/v0/load_question', methods=['GET'])
@requires_cache(['question', 'sql', 'df', 'fig_json', 'followup_questions'])
def load_question(id: str, question, sql, df, fig_json, followup_questions):
    """
    Load a question based on the ID provided.
    ---
    parameters:
        - name: id
          type: string
          required: true
          description: The ID of the question to load.
    responses:
        200:
            description: The loaded question.
            schema:
                type: object
                properties:
                    type:
                        type: string
                        example: question_cache
                    id:
                        type: string
                        example: 12345
                    question:
                        type: string
                        example: "What is the average salary?"
                    sql:
                        type: string
                        example: "SELECT AVG(salary) FROM employees"
                    df:
                        type: array
                        items:
                            type: object
                        example: [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
                    fig:
                        type: object
                        example: {"data": [{"x": [1, 2, 3], "y": [4, 5, 6]}]}
                    followup_questions:
                        type: array
                        items:
                            type: string
                        example: ["What is the average salary?", "How many employees are there?"]
    """
    try:
        return jsonify(
            {
                "type": "question_cache", 
                "id": id,
                "question": question,
                "sql": sql,
                "df": df.head(10).to_json(orient='records'),
                "fig": fig_json,
                "followup_questions": followup_questions,
            })

    except Exception as e:
        return jsonify({"type": "error", "error": str(e)})

@app.route('/api/v0/get_question_history', methods=['GET'])
def get_question_history():
    """
    Get the question history from the cache.
    ---
    responses:
        200:
            description: The question history.
            schema:
                type: object
                properties:
                    type:
                        type: string
                        example: question_history
                    questions:
                        type: array
                        items:
                            type: string
                        example: ["What is the average salary?", "How many employees are there?"]
    """
    return jsonify({"type": "question_history", "questions": cache.get_all(field_list=['question']) })

@app.route('/')
def root():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    app.run(debug=True)
