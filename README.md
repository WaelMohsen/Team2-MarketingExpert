# Team2-MarketingExpert

This is Team 2 Implementation for the Marketing Engine (Making marketing simple for non-marketers. Auto-optimized recommendations in plain
language.) 

## Requirements

- Python 3.8 or later

#### Install Python using MiniConda

1) Download and install MiniConda from [here](https://docs.anaconda.com/free/miniconda/#quick-command-line-install)
2) Create a new environment using the following command:
```bash
$ conda create -n market-engine python=3.8
```
3) Activate the environment:
```bash
$ conda activate market-engine
```


## Installation

### Install the required packages

```bash
$ pip install -r requirements.txt
```

### Setup the environment variables

```bash
$ cp .env.example .env
```

Set your environment variables in the `.env` file. Like `OPENAI_API_KEY` value.

## Running the Application

To start the application, run:

```bash
$ streamlit run app.py
```

