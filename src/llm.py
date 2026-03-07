import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Helper Functions ---
def load_prompt(filename):
    """Loads a prompt from the 'prompts' directory."""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filepath = os.path.join(base_dir, "prompts", filename)
        with open(filepath, "r", encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading prompt {filename}: {e}")
        return ""

def build_input_payload(category, metrics):
    """
    يبني الـ JSON المتوافق مع الـ INPUT FORMAT الجديد اللي التيم طالبه
    """
    # هنفترض إنك بتجمع الداتا دي من الـ metrics اللي جاية للفانكشن
    payload = {
        "campaign_target": {
            "primary_goal": category,
            "kpis": ["CTR", "Conversion Rate", "ROAS", "CPA"]
        },
        "business_domain": {
            "industry": "Assumed from Context", 
            "offering": "Product/Service",
            "audience": "Target Customers",
            "funnel_stage": "conversion" # Default or dynamic based on category
        },
        "campaign_platforms_data": [
            {
                "platform": "Aggregate/Unknown", # Or dynamic if you have it in metrics
                "objective": category,
                "metrics": {
                    "spend": metrics.get('Total Spend', None),
                    "impressions": metrics.get('Total Impressions', None),
                    "clicks": metrics.get('Total Clicks', None),
                    "ctr": metrics.get('CTR', None),
                    "conversions": metrics.get('Total Conversions', None),
                    "conversion_rate": metrics.get('Conversion Rate', None),
                    "cpa": metrics.get('CPA', None),
                    "revenue": metrics.get('Total Revenue', None),
                    "roas": metrics.get('ROAS', None)
                }
            }
        ]
    }
    return json.dumps(payload, indent=2)


# --- The Main Orchestrator ---
def generate_response(query, category, metrics):
    """
    الآن تعمل على خطوتين: (LLM 1 للتحليل) ثم (LLM 2 للتوصيات)
    """
    # 1. Map category to the NEW split prompt files
    category_map = {
        "Customer Acquisition": {
            "analysis": "customer_acquisition_analysis.md",
            "recommendation": "customer_acquisition_rec.md"
        }
        # Add other categories here...
    }
    
    files = category_map.get(category)
    if not files:
        return "Error: Category mapping not found for new architecture."

    # 2. Load System Prompts
    sys_prompt_analysis = load_prompt(files["analysis"])
    sys_prompt_rec = load_prompt(files["recommendation"])

    # 3. Build the User Input (The JSON Payload)
    user_payload_str = build_input_payload(category, metrics)

    try:
        # ==========================================
        # STEP 1: LLM 1 - Data Insights & Analysis
        # ==========================================
        print("Running LLM 1: Analysis Phase...")
        analysis_response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={ "type": "json_object" }, # يجبر الموديل يرجع JSON فقط
            messages=[
                {"role": "system", "content": sys_prompt_analysis},
                {"role": "user", "content": f"Analyze this campaign data:\n{user_payload_str}"}
            ],
            temperature=0.2,
        )
        
        # استخراج التحليل كـ String (هو في الأصل JSON مبعوت من الموديل)
        analysis_result = analysis_response.choices[0].message.content

        # ==========================================
        # STEP 2: LLM 2 - Recommendations
        # ==========================================
        print("Running LLM 2: Recommendation Phase...")
        rec_response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": sys_prompt_rec},
                {"role": "user", "content": f"Based on this analysis, generate actionable recommendations:\n{analysis_result}"}
            ],
            temperature=0.2,
        )
        
        recommendations_result = rec_response.choices[0].message.content

        # ==========================================
        # STEP 3: Combine and Return
        # ==========================================
        # ندمج الاتنين مع بعض عشان نرجعهم للـ Frontend أو نخزنهم
        final_output = {
            "analysis_data": json.loads(analysis_result),
            "recommendations_data": json.loads(recommendations_result)
        }
        
        return json.dumps(final_output, indent=2)

    except Exception as e:
        return f"Error generating response: {e}"