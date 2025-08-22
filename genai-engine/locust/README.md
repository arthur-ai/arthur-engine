# Arthur GenAI Engine Performance Test

## Assemble
Assemble the performance test suite for execution and distribution by running the below from this directory.
It produces a zip file, `genai-engine-perf.zip`, containing the performance test suite.
```
./assemble.sh
```

## Run
### Setup
Python virtual environment (example below for macOS):
```
brew install pyenv
brew install pyenv-virtualenv
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

pyenv install 3.13
pyenv virtualenv 3.13 locust
pyenv activate locust
```

Install dependencies:
```
pip install -r requirements.txt
```

GenAI Engine API key with TASK-ADMIN role:
```
export GENAI_ENGINE_ADMIN_KEY=<your-api-key>
```

### UI
```
locust
```

### CLI
```
locust --headless --users 1 --spawn-rate 3 -H https://<your-genai-engine-hostname> -t 1m --logfile out-locust-genai-engine.log --html out-locust-genai-engine.html
```

### Options
Enable response validation:
```
export VALIDATE_RESPONSE=True # Default: False
```

Specify rules file:
```
export RULES_FILE=data/rules-min.json # Default: data/rules-min.json
```

Specify inferences file:
```
export INFERENCES_FILE=data/inferences-generic.json # Default: data/inferences-generic.json
```

Specify prompts Parquet file (overrides the INFERENCES_FILE and sets VALIDATE_RESPONSE to False):
```
export PROMPTS_FILE=data/prompts.parquet # Default: None
```

Specify wait time min and max:
```
export WAIT_TIME_MIN=0.1 # Default: 0.1
export WAIT_TIME_MAX=5.0 # Default: 5.0
```
