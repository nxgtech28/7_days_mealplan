from fastapi import FastAPI, HTTPException
from typing import Dict, List
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os
import re
from groq import Groq
from fastapi.middleware.cors import CORSMiddleware
import json

# Load environment variables
load_dotenv()

app = FastAPI(title="Meal Planner API")

# --- INITIALIZATION ---
try:
    # Priority: Environment variable > config.json
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    # If not in environment, try config.json (for local development)
    if not GROQ_API_KEY:
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                content = f.read().strip()
                if content:
                    config = json.loads(content)
                    GROQ_API_KEY = config.get("groq_api_key", "")
                    if not GROQ_MODEL or GROQ_MODEL == "llama-3.3-70b-versatile":
                        GROQ_MODEL = config.get("model", "llama-3.3-70b-versatile")

    if not GROQ_API_KEY:
        print("⚠️ Warning: GROQ_API_KEY not found. API calls will fail.")
    else:
        client = Groq(api_key=GROQ_API_KEY)

except Exception as e:
    print(f"❌ Error initializing configuration: {str(e)}")
    raise

# Import food datasets
try:
    from food_data import (
        snacks, STATE_FOOD_MAPPING,
    )
except ImportError:
    print("❌ Error: food_data.py not found or incomplete.")
    STATE_FOOD_MAPPING = {}
    snacks = {}

# --- HELPER FUNCTIONS ---

def detect_regional_preferences(input_text: str) -> tuple:
    """Detect regional preferences and diet type from input text"""
    input_lower = input_text.lower()
    detected_states = []
    
    state_keywords = {
        'kerala': ['kerala', 'ker'],
        'tamil nadu': ['tamil nadu', 'tamilnadu', 'tamil_nadu', 'tamil', 'tn'],
        'delhi': ['delhi', 'dilli'],
        'karnataka': ['karnataka', 'kar', 'ka'],
        'andhra pradesh': ['andhra pradesh', 'andhra', 'ap'],
        'telangana': ['telangana', 'tel', 'ts'],
        'haryana': ['haryana', 'hry'],
        'punjab': ['punjab', 'pb'],
        'rajasthan': ['rajasthan', 'rj'],
        'uttar pradesh': ['uttar pradesh', 'up'],
        'bihar': ['bihar', 'br'],
        'himachal pradesh': ['himachal pradesh', 'hp'],
        'jammu and kashmir': ['jammu', 'kashmir', 'jk'],
        'jharkhand': ['jharkhand', 'jh'],
        'uttarakhand': ['uttarakhand', 'uk'],
    }
    
    for state, keywords in state_keywords.items():
        if any(keyword in input_lower for keyword in keywords):
            detected_states.append(state)
    
    # Detect diet type: vegan > vegetarian > non-veg
    diet_type = "non-veg"  # default
    
    # Try to parse JSON structure from input_text to extract cuisine preferences
    try:
        # Look for JSON-like structure in the input
        if '{' in input_text and '}' in input_text:
            # Try to extract and parse JSON from input
            json_start = input_text.find('{')
            json_end = input_text.rfind('}') + 1
            if json_start < json_end:
                json_str = input_text[json_start:json_end]
                try:
                    parsed = json.loads(json_str)
                    # Check if cuisine field exists and contains 'veg'
                    if 'cuisine' in parsed:
                        cuisine = parsed['cuisine']
                        if isinstance(cuisine, dict):
                            # Check all values in cuisine dict for 'veg'
                            for key, value in cuisine.items():
                                if isinstance(value, list):
                                    if 'veg' in [str(v).lower() for v in value]:
                                        diet_type = "veg"
                                        break
                                elif isinstance(value, str) and 'veg' in value.lower():
                                    diet_type = "veg"
                                    break
                except json.JSONDecodeError:
                    # If JSON parsing fails, try pattern matching for cuisine: {...veg...}
                    # Look for patterns like "cuisine: {Indian: [veg]" or "cuisine.*\[.*veg"
                    if 'cuisine' in input_lower:
                        # Check for patterns like [veg] or : [veg] or {.*veg
                        # Match: cuisine: {Indian: [veg] or cuisine: {...[veg]...} or [veg] after cuisine
                        if re.search(r'cuisine.*\[.*veg|cuisine.*\{.*veg|indian.*\[.*veg|\[.*veg.*\]', input_lower):
                            diet_type = "veg"
    except Exception:
        pass
    
    # Fallback to string matching if JSON parsing didn't work
    if diet_type == "non-veg":
        if any(keyword in input_lower for keyword in ['vegan', 'plant-based', 'no dairy', 'no eggs']):
            diet_type = "vegan"
        elif any(keyword in input_lower for keyword in ['veg only', 'vegetarian only', 'no non-veg', 'vegetarian']):
            diet_type = "veg"
        elif 'cuisine' in input_lower and 'veg' in input_lower:
            # Check if 'veg' appears in context of cuisine preference (not part of 'vegetarian')
            # Look for patterns like "indian: [veg]" or "veg]" or "[veg" near cuisine
            if re.search(r'cuisine.*\[.*veg|cuisine.*\{.*veg|indian.*\[.*veg|\[.*veg.*\]', input_lower):
                diet_type = "veg"
    
    detected_states = list(dict.fromkeys(detected_states))
    return detected_states, diet_type

def parse_user_input(input_text: str) -> dict:
    """Parse user input and extract details"""
    input_lower = input_text.lower()
    user_data = {}
    
    # Weight
    weight_match = re.search(r'(?:current\s+)?weight:\s*(\d+(?:\.\d+)?)\s*kg', input_lower)
    if weight_match:
        user_data['weight'] = float(weight_match.group(1))
    
    # Height
    height_match = re.search(r'height:\s*(\d+(?:\.\d+)?)\s*cm', input_lower)
    if height_match:
        user_data['height'] = float(height_match.group(1))
    
    # Target Weight
    target_match = re.search(r'target\s*weight:\s*(\d+(?:\.\d+)?)\s*kg', input_lower)
    if target_match:
        user_data['target_weight'] = float(target_match.group(1))
    
    # Age
    age_match = re.search(r'age:\s*(\d+)', input_lower)
    if age_match:
        user_data['age'] = int(age_match.group(1))
    
    # Gender
    if 'female' in input_lower:
        user_data['gender'] = 'Female'
    elif 'male' in input_lower:
        user_data['gender'] = 'Male'
    
    # Allergies
    allergy_match = re.search(r'allerg(?:ies|y):\s*([^,]+)', input_lower)
    user_data['allergies'] = allergy_match.group(1).strip() if allergy_match else "None"
    
    # Health Conditions
    health_match = re.search(r'health\s*conditions?:\s*([^,]+)', input_lower)
    user_data['health_condition'] = health_match.group(1).strip() if health_match else "None"
    
    # Activity Level
    if 'sedentary' in input_lower:
        user_data['activity_level'] = 'Sedentary'
    elif 'moderate' in input_lower:
        user_data['activity_level'] = 'Moderately Active'
    elif 'active' in input_lower:
        user_data['activity_level'] = 'Very Active'
    else:
        user_data['activity_level'] = 'Sedentary'
    
    # Fitness Goal
    if 'gain' in input_lower or 'weight gain' in input_lower:
        user_data['goal'] = 'gain'
    elif 'lose' in input_lower or 'weight loss' in input_lower:
        user_data['goal'] = 'lose'
    else:
        user_data['goal'] = 'maintain'
    
    return user_data

def calculate_bmi(weight: float, height: float) -> float:
    """Calculate BMI"""
    return round(weight / ((height / 100) ** 2), 2)

def calculate_target_calorie(weight: float, height: float, age: int, gender: str, activity_level: str, goal: str) -> int:
    """Calculate target daily calorie requirement"""
    # BMR calculation (Mifflin-St Jeor Equation)
    if gender == 'Male':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    
    # Activity multipliers
    multipliers = {
        'Sedentary': 1.2,
        'Moderately Active': 1.55,
        'Very Active': 1.725
    }
    
    tdee = bmr * multipliers.get(activity_level, 1.2)
    
    # Adjust for goal
    if goal == 'gain':
        tdee += 300
    elif goal == 'lose':
        tdee -= 500
    
    return int(tdee)

def format_food_dataset_for_prompt(food_dataset: dict, diet_type: str) -> str:
    """Format food dataset as JSON for LLM (filtered by diet type)"""
    if not food_dataset: 
        return json.dumps({"error": "No food dataset available."}, indent=2)
    
    filtered_dataset = {}
    
    for meal in ["breakfast", "lunch", "dinner"]:
        if meal not in food_dataset:
            continue
            
        data = food_dataset[meal]
        meal_data = {}
        
        # Extract base_items based on diet type
        if "base_items" in data:
            base_items = data["base_items"]
            if isinstance(base_items, dict):
                # New structure: base_items has veg, non_veg, vegan sub-sections
                if diet_type == "vegan" and "vegan" in base_items:
                    meal_data["base_items"] = base_items["vegan"]
                elif diet_type == "veg" and "veg" in base_items:
                    meal_data["base_items"] = base_items["veg"]
                elif diet_type == "non-veg" and "non_veg" in base_items:
                    meal_data["base_items"] = base_items["non_veg"]
                else:
                    # Fallback: use the whole base_items if structure is old
                    meal_data["base_items"] = base_items
            else:
                # Old structure: base_items is direct
                meal_data["base_items"] = base_items
        
        # Include appropriate items section based on diet type
        if diet_type == "vegan":
            # Vegan: Include only vegan_items
            if "vegan_items" in data:
                vegan_data = data["vegan_items"]
                meal_data["vegan_items"] = {}
                
                if isinstance(vegan_data, dict):
                    if "gravy" in vegan_data and vegan_data["gravy"]:
                        meal_data["vegan_items"]["gravy"] = vegan_data["gravy"]
                    if meal in ["lunch", "dinner"] and "dry" in vegan_data and vegan_data["dry"]:
                        meal_data["vegan_items"]["dry"] = vegan_data["dry"]
        elif diet_type == "non-veg":
            # Non-veg: Include only non_veg_items
            if "non_veg_items" in data:
                non_veg_data = data["non_veg_items"]
                meal_data["non_veg_items"] = {}
                
                if isinstance(non_veg_data, dict):
                    if "gravy" in non_veg_data and non_veg_data["gravy"]:
                        meal_data["non_veg_items"]["gravy"] = non_veg_data["gravy"]
                    if meal in ["lunch", "dinner"] and "dry" in non_veg_data and non_veg_data["dry"]:
                        meal_data["non_veg_items"]["dry"] = non_veg_data["dry"]
        else:
            # Veg: Include only veg_items
            if "veg_items" in data:
                veg_data = data["veg_items"]
                meal_data["veg_items"] = {}
                
                if isinstance(veg_data, dict):
                    if "gravy" in veg_data and veg_data["gravy"]:
                        meal_data["veg_items"]["gravy"] = veg_data["gravy"]
                    if meal in ["lunch", "dinner"] and "dry" in veg_data and veg_data["dry"]:
                        meal_data["veg_items"]["dry"] = veg_data["dry"]
        
        if meal_data:
            filtered_dataset[meal] = meal_data
    
    return json.dumps(filtered_dataset, indent=2)

def format_snacks_for_prompt(snacks_data: dict, diet_type: str) -> str:
    """Format snacks dataset as JSON for LLM (filtered by diet type)"""
    if not snacks_data:
        return "{}"
    
    filtered_snacks = {}
    
    # Filter snacks based on diet type
    if diet_type == "vegan":
        if "vegan_snacks" in snacks_data:
            filtered_snacks["vegan_snacks"] = snacks_data["vegan_snacks"]
        if "beverages" in snacks_data and isinstance(snacks_data["beverages"], dict):
            if "vegan" in snacks_data["beverages"]:
                filtered_snacks["beverages"] = {"vegan": snacks_data["beverages"]["vegan"]}
    elif diet_type == "non-veg":
        if "non_veg_snacks" in snacks_data:
            filtered_snacks["non_veg_snacks"] = snacks_data["non_veg_snacks"]
        if "veg_snacks" in snacks_data:
            filtered_snacks["veg_snacks"] = snacks_data["veg_snacks"]
        if "beverages" in snacks_data and isinstance(snacks_data["beverages"], dict):
            if "non_veg" in snacks_data["beverages"]:
                filtered_snacks["beverages"] = {"non_veg": snacks_data["beverages"]["non_veg"]}
    else:  # veg
        if "veg_snacks" in snacks_data:
            filtered_snacks["veg_snacks"] = snacks_data["veg_snacks"]
        if "beverages" in snacks_data and isinstance(snacks_data["beverages"], dict):
            if "veg" in snacks_data["beverages"]:
                filtered_snacks["beverages"] = {"veg": snacks_data["beverages"]["veg"]}
    
    return json.dumps(filtered_snacks, indent=2)

def build_llm_prompt(target_calorie: int, target_weight: float, allergies: str, health_conditions: str, 
                     diet_type: str, food_dataset_json: str, snacks_json: str) -> str:
    """Build the complete prompt for LLM
    
    Note: Food items in the dataset use different units:
    - 'gram': calories per gram (e.g., 0.7 = 0.7 kcal/gram)
    - 'ml': calories per ml (e.g., 0.2 = 0.2 kcal/ml)
    - 'piece', 'cup', 'serving', 'tbsp', etc.: calories per unit
    The LLM must calculate: Quantity × Calories per unit based on the unit type.
    """
    template_path = os.path.join(os.path.dirname(__file__), "prompt_template.json")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template = json.loads(f.read())
    
    system_prompt = template.get("system_prompt", "")
    user_prompt = template.get("user_prompt", {})
    
    # Calculate calorie range
    target_calorie_min = target_calorie - 50
    target_calorie_max = target_calorie + 50
    
    # Build prompt
    prompt = f"{system_prompt}\n\n"
    
    prompt += f"TARGET CALORIE: {target_calorie} kcal per day\n"
    prompt += f"TARGET WEIGHT: {target_weight} kg\n"
    prompt += f"ALLERGIES: {allergies}\n"
    prompt += f"HEALTH CONDITIONS: {health_conditions}\n"
    prompt += f"DIET TYPE: {diet_type}\n\n"
    
    prompt += "FOOD DATASET:\n"
    prompt += f"{food_dataset_json}\n\n"
    
    prompt += "SNACKS DATASET:\n"
    prompt += f"{snacks_json}\n\n"
    
    # Meal structure rules
    meal_rules = user_prompt.get("meal_structure_rules", {})
    if diet_type == "non-veg":
        rules = meal_rules.get("non_veg", {})
        prompt += "MEAL STRUCTURE RULES (NON-VEG):\n"
    elif diet_type == "vegan":
        rules = meal_rules.get("vegan", {})
        prompt += "MEAL STRUCTURE RULES (VEGAN):\n"
    else:
        rules = meal_rules.get("veg", {})
        prompt += "MEAL STRUCTURE RULES (VEG):\n"
    
    for meal_type in ["breakfast", "lunch", "dinner"]:
        if meal_type in rules:
            meal_rule = rules[meal_type]
            prompt += f"{meal_type.upper()}:\n"
            prompt += f"  Option A: {meal_rule.get('option_a', '')}\n"
            prompt += f"  Option B: {meal_rule.get('option_b', '')}\n"
    prompt += "\n"
    
    # Calorie calculation process
    calorie_process = user_prompt.get("calorie_calculation_process", {})
    if calorie_process:
        prompt += "=" * 80 + "\n"
        if calorie_process.get("title"):
            prompt += f"{calorie_process.get('title')}\n"
        prompt += "=" * 80 + "\n"
        
        # Steps
        steps = calorie_process.get("steps", [])
        for step in steps:
            step = step.replace("{target_calorie}", str(target_calorie))
            step = step.replace("{target_calorie_min}", str(target_calorie_min))
            step = step.replace("{target_calorie_max}", str(target_calorie_max))
            prompt += f"{step}\n"
        prompt += "\n"
        
        # Critical notes
        critical_notes = calorie_process.get("critical_notes", [])
        if critical_notes:
            prompt += "CRITICAL NOTES:\n"
            for note in critical_notes:
                note = note.replace("{target_calorie}", str(target_calorie))
                note = note.replace("{target_calorie_min}", str(target_calorie_min))
                note = note.replace("{target_calorie_max}", str(target_calorie_max))
                # Calculate example values for better understanding
                example_low_total = 1800
                calorie_diff = target_calorie - example_low_total
                multiplier = round(target_calorie / example_low_total, 2) if example_low_total > 0 else 1.0
                note = note.replace("{target_calorie_minus_1856}", str(calorie_diff))
                note = note.replace("{target_calorie_ratio}", str(multiplier))
                prompt += f"- {note}\n"
        prompt += "\n"
    
    # Critical rules
    critical_rules = user_prompt.get("critical_rules", [])
    prompt += "CRITICAL RULES:\n"
    # Calculate example values for better understanding
    example_low_total = 1800
    calorie_diff = target_calorie - example_low_total
    multiplier = round(target_calorie / example_low_total, 2) if example_low_total > 0 else 1.0
    
    for rule in critical_rules:
        # Replace placeholders
        rule = rule.replace("{target_calorie}", str(target_calorie))
        rule = rule.replace("{target_calorie_min}", str(target_calorie_min))
        rule = rule.replace("{target_calorie_max}", str(target_calorie_max))
        rule = rule.replace("{target_calorie_ratio}", str(multiplier))
        rule = rule.replace("{target_calorie_minus_1856}", str(calorie_diff))
        rule = rule.replace("{allergies}", allergies)
        rule = rule.replace("{health_conditions}", health_conditions)
        prompt += f"- {rule}\n"
    prompt += "\n"
    
    # Output format
    output_format = user_prompt.get("output_format", {})
    prompt += "=" * 80 + "\n"
    prompt += "OUTPUT FORMAT - CRITICAL INSTRUCTIONS:\n"
    prompt += "=" * 80 + "\n"
    
    # Title and critical instruction
    if output_format.get("title"):
        prompt += f"{output_format.get('title')}\n"
    if output_format.get("critical_instruction"):
        prompt += f"{output_format.get('critical_instruction')}\n\n"
    
    # Format template
    format_template = output_format.get('format_template', output_format.get('format', ''))
    format_template = format_template.replace("{target_calorie}", str(target_calorie))
    format_template = format_template.replace("{target_weight}", str(target_weight))
    prompt += f"FORMAT TEMPLATE:\n{format_template}\n\n"
    
    # Strict forbidden items
    if output_format.get("strict_forbidden"):
        prompt += "STRICTLY FORBIDDEN IN OUTPUT:\n"
        for forbidden in output_format.get("strict_forbidden", []):
            prompt += f"- {forbidden}\n"
        prompt += "\n"
    
    # Rules
    prompt += "OUTPUT RULES:\n"
    for rule in output_format.get("rules", []):
        rule = rule.replace("{target_calorie}", str(target_calorie))
        rule = rule.replace("{target_weight}", str(target_weight))
        prompt += f"- {rule}\n"
    
    prompt += "\n" + "=" * 80 + "\n"
    prompt += "REMEMBER: Output ONLY the bracketed string. NO introductory text. NO notes. NO explanations.\n"
    prompt += "Start with [Target weight]: and end with [day 7] data.\n"
    prompt += "=" * 80 + "\n"
    
    return prompt

def parse_meal_plan_response(response: str) -> Dict:
    """Parse the LLM response into structured format"""
    result = {}
    
    # Target Weight - capture value until closing bracket or comma
    target = re.search(r'\[Target weight\]:\[([^\]]+)\]', response, re.IGNORECASE)
    if target:
        # Extract just the weight value, stopping at comma if present
        weight_value = target.group(1).strip()
        # Remove any trailing comma or extra text
        if ',' in weight_value:
            weight_value = weight_value.split(',')[0].strip()
        result["target_weight"] = weight_value
    
    # Macros (skip Total Calories - it's set from Python)
    result["macros"] = {}
    for macro in ["Total Carbs", "Total Protein", "Total Fat", "Total Fiber"]:
        # Match [Macro]:[value] format, stopping at closing bracket
        match = re.search(rf'\[{re.escape(macro)}\]:\[([^\]]+)\]', response, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # Remove any trailing comma or extra text
            if ',' in value:
                value = value.split(',')[0].strip()
            result["macros"][macro] = value
        
    # Meal Plan
    days = []
    day_blocks = re.split(r'\[day \d+\]:', response, flags=re.IGNORECASE)
    
    if len(day_blocks) > 1:
        day_blocks = day_blocks[1:]
    
    for i, block in enumerate(day_blocks):
        day_data = {"day": i + 1, "meals": {}, "calories": {}, "short_names": {}}
        
        for meal in ["Breakfast", "Snack 1", "Lunch", "Snack 2", "Dinner"]:
            pattern = rf'\[{meal}\]:\[(.*?)\](?:\[Short Name\]:\[(.*?)\])?(?:\[Calories\]:\[(.*?)\])?'
            match = re.search(pattern, block, re.IGNORECASE)
            
            if match:
                content = match.group(1).strip()
                short_name = match.group(2).strip() if match.group(2) else ""
                cal = match.group(3).strip() if match.group(3) else "0"
                
                day_data["meals"][meal] = content
                day_data["short_names"][meal] = short_name
                day_data["calories"][meal] = cal
        
        if day_data["meals"]:
            days.append(day_data)
            
    result["meal_plan"] = days
    return result

# --- API ENDPOINTS ---

class MealRequest(BaseModel):
    input_text: str

@app.post("/mealplan")
async def get_meal_plan(request: MealRequest):
    try:
        # 1. Parse user input
        user_data = parse_user_input(request.input_text)
        
        # Validate required fields
        if 'weight' not in user_data or 'height' not in user_data:
            raise HTTPException(status_code=400, detail="Weight and height are required")
        
        # 2. Calculate BMI
        bmi = calculate_bmi(user_data['weight'], user_data['height'])
        
        # 3. Calculate target calorie
        target_calorie = calculate_target_calorie(
            user_data['weight'],
            user_data['height'],
            user_data.get('age', 25),
            user_data.get('gender', 'Male'),
            user_data.get('activity_level', 'Sedentary'),
            user_data.get('goal', 'maintain')
        )
        
        # 4. Detect regional preferences and diet type
        states, diet_type = detect_regional_preferences(request.input_text)
        
        # 5. Get food dataset
        food_dataset = None
        if states:
            state_name = states[0]
            key = next((k for k in STATE_FOOD_MAPPING.keys() if k.lower() == state_name.lower()), None)
            food_dataset = STATE_FOOD_MAPPING.get(key)
        
        if not food_dataset:
            raise HTTPException(status_code=400, detail="Regional cuisine not found or not supported")
        
        # Format datasets
        food_dataset_json = format_food_dataset_for_prompt(food_dataset, diet_type)
        snacks_json = format_snacks_for_prompt(snacks, diet_type)
        
        # 6. Build LLM prompt
        target_weight = user_data.get('target_weight', user_data['weight'])
        llm_prompt = build_llm_prompt(
            target_calorie=target_calorie,
            target_weight=target_weight,
            allergies=user_data.get('allergies', 'None'),
            health_conditions=user_data.get('health_condition', 'None'),
            diet_type=diet_type,
            food_dataset_json=food_dataset_json,
            snacks_json=snacks_json
        )
        
        print(f"\n📤 Sending Prompt to LLM... (Length: {len(llm_prompt)})")
        
        # 7. Call LLM
        if not GROQ_API_KEY:
            raise HTTPException(status_code=500, detail="GROQ_API_KEY missing in config")

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": llm_prompt},
                {"role": "user", "content": f"Generate a 7-day meal plan with target calorie: {target_calorie} kcal/day"}
            ],
            temperature=0.3,
            max_tokens=6000
        )
        
        ai_response = response.choices[0].message.content
        print(f"\n📥 Received Response (Length: {len(ai_response)})")
        
        # 8. Parse response
        result = parse_meal_plan_response(ai_response)
        
        if not result.get("meal_plan"):
             print("⚠️ Parsing failed, returning raw response")
             return JSONResponse(content={"raw_response": ai_response, "parsed": False})

        # Set Total Calories from Python (not from LLM response)
        if "macros" not in result:
            result["macros"] = {}
        result["macros"]["Total Calories"] = str(target_calorie)

        return JSONResponse(content=result)

    except json.JSONDecodeError as je:
        print(f"❌ JSON Error: {str(je)}")
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(je)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
