import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CATEGORIES = [
    "Customer Acquisition",
    "Customer Satisfaction",
    "Revenue Growth",
    "Customer Retention"
]

# Removed classify_query function as it's no longer needed

def load_prompt(filename, **kwargs):
    """
    Loads a prompt from the 'prompts' directory and formats it with kwargs.
    """
    try:
        # Assuming the 'prompts' directory is one level up from 'src'
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filepath = os.path.join(base_dir, "prompts", filename)
        
        with open(filepath, "r") as f:
            template = f.read()
            return template.format(**kwargs)
    except Exception as e:
        print(f"Error loading prompt {filename}: {e}")
        return ""

def classify_query(query):
    """
    Classifies the user query into one of the predefined categories using GPT-4o-mini.
    """
    
    prompt = load_prompt("classification.md", query=query)
    # The saved file has a format string {query}, so we need to run .format on it.
    # The load_prompt helper we added handles this.

    try:

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that classifies marketing queries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        category = response.choices[0].message.content.strip()
        # Clean up any potential extra text like "Category: "
        for cat in CATEGORIES:
            if cat.lower() in category.lower():
                return cat
        return "General"
    except Exception as e:
        print(f"Error classifying query: {e}")
        return "General"

def generate_response(query, category, metrics):
    """
    Generates a response based on the category using a specific prompt file.
    """
    metrics_str = json.dumps(metrics, indent=2)
    
    # Map category to specific prompt file
    category_map = {
        "Customer Acquisition": "customer_acquisition.md",
        "Customer Satisfaction": "customer_satisfaction.md",
        "Revenue Growth": "revenue_growth.md",
        "Customer Retention": "customer_retention.md"
    }

    # Get the correct filename, default to generic response_generation.md if not found
    prompt_file = category_map.get(category, "response_generation.md")
    
    # Load prompt with available arguments (some prompts might not use all args, but that's okay for .format if keys exist)
    # We pass extra context like 'time_period' just in case the prompt uses it
    system_prompt = load_prompt(
        prompt_file, 
        category=category, 
        metrics_str=metrics_str,
        time_period="Current Data Snapshot" 
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating response: {e}"
