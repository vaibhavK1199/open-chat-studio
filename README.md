# Open Chat Studio

Experiments with AI, GPT and LLMs.

## Installation

Setup a virtualenv and install requirements
(this example uses [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/)):

```bash
mkvirtualenv gpt_playground -p python3.11
pip install -r dev-requirements.txt
```

Python 3.11 is recommended, though anything between 3.9 and 3.11 should work.

## Set up database

Create a database named `gpt_playground`.

```
createdb gpt_playground
```

or if you're using docker, start the container with

```
docker run -d --name gpt-postgres -p 5432:5432 -e POSTGRES_PASSWORD=*** -e POSTGRES_USER=postgres -e POSTGRES_DATABASE=gpt_playground postgres:14
```
then create the DB
```
docker exec -it gpt-postgres createdb -U postgres gpt_playground
```

Create database migrations:

```
./manage.py makemigrations
```

Create database tables:

```
./manage.py migrate
```

## Running server

```bash
./manage.py runserver
```

## Building front-end

To build JavaScript and CSS files, first install npm packages:

```bash
npm install
```

Then build (and watch for changes locally):

```bash
npm run dev-watch
```

## Running Redis

Redis is needed by Celery to run background tasks.

You can set up Redis in docker using:

```bash
docker run -d -p 6379:6379 --name redis redis
```

## Running Celery

Celery can be used to run background tasks.

**Note:** Celery is needed to get a response from the LLM, so you'll need to run this if you want to test end-to-end conversations.

You can run it using:

```bash
celery -A gpt_playground worker -l INFO
```

Or with celery beat (for scheduled tasks):

```bash
celery -A gpt_playground worker -l INFO -B
```

## Updating translations

**Docker:**

```bash
make translations
```

**Native:**

```bash
./manage.py makemessages --all --ignore node_modules --ignore venv
./manage.py makemessages -d djangojs --all --ignore node_modules --ignore venv
./manage.py compilemessages
```

## Installing Git commit hooks

To install the Git commit hooks run the following:

```shell
$ pre-commit install --install-hooks
```

Once these are installed they will be run on every commit.

## Running Tests

To run tests:

```bash
./manage.py test
```

Or to test a specific app/module:

```bash
./manage.py test apps.utils.tests.test_slugs
```

On Linux-based systems you can watch for changes using the following:

```bash
find . -name '*.py' | entr python ./manage.py test apps.utils.tests.test_slugs
```


## Customizations

Copy the `.env.example` file to `.env` and set any values that you need.
You should also add your OpenAI key to this file:

```
OPENAI_API_KEY="sk-***"
```

### Testing bots

To test a bot, first create an experiment. This can be done in the Django admin.

After doing that you can use the UI to create a new chat session against the experiment.

Note that celery needs to be running and your `OPENAI_API_KEY` needs to be set in order to get responses from the bot.

You can also run experiments on the command line using:

```bash
python manage.py run_experiment <experiment_pk>
```

#### Testing bots through Channels
Telegram - To test the webhooks, you can use a tool like ngrok to forward webhook data to your local machine.
