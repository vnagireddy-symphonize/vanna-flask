# vanna-flask
Web server for chatting with your database



https://github.com/vanna-ai/vanna-flask/assets/7146154/5794c523-0c99-4a53-a558-509fa72885b9



# Setup

## Set your environment variables
```
VANNA_MODEL=
VANNA_API_KEY=

# for sqlite ...
DATABASE_URL=

# for snowflake ...
SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USERNAME=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_DATABASE=
SNOWFLAKE_WAREHOUSE=
```

## Create virtual environment
```
python -m venv venv
```

## Activate virtual environment
```
source ./venv/bin/activate
```

## Install dependencies
```
pip install -r requirements.txt
```

## Run the server
```
python app.py
```

