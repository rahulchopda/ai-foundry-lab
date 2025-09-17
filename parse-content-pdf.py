import json
import re
import time
from typing import Dict, List

def load_document_ai_result(file_path: str) -> Dict:
    """Load the Document AI result JSON"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_recipe_components(markdown_text: str) -> Dict:
    """Parse recipe content and extract structured components"""
    
    print("🔄 Step 1: Parsing recipe structure...")
    time.sleep(0.5)
    
    # Extract title
    title_match = re.search(r'^# (.+)', markdown_text, re.MULTILINE)
    title = title_match.group(1) if title_match else "Unknown Recipe"
    print(f"📝 Found recipe: {title}")
    
    # Extract ingredients
    ingredients_section = re.search(r'## Ingredients\n\n(.*?)\n\n', markdown_text, re.DOTALL)
    ingredients = []
    if ingredients_section:
        ingredient_lines = ingredients_section.group(1).split('\n')
        ingredients = [line.strip('- ').strip() for line in ingredient_lines if line.strip().startswith('-')]
    
    print(f"🥗 Found {len(ingredients)} ingredients")
    
    # Extract instructions
    instructions_match = re.search(r'Instructions\n\n(.*)', markdown_text, re.DOTALL)
    instructions = []
    if instructions_match:
        instruction_text = instructions_match.group(1)
        steps = re.split(r'\n\d+\.\s+', instruction_text)
        instructions = [step.strip() for step in steps if step.strip()]
    
    print(f"👨‍🍳 Found {len(instructions)} cooking steps")
    
    return {
        "title": title,
        "ingredients": ingredients,
        "instructions": instructions,
        "ingredient_count": len(ingredients),
        "step_count": len(instructions)
    }

def create_shopping_list(recipe_data: Dict) -> List[str]:
    """Extract just the ingredient names for a shopping list"""
    print("\n🛒 Step 2: Generating smart shopping list...")
    time.sleep(0.5)
    
    shopping_list = []
    for ingredient in recipe_data['ingredients']:
        # Remove measurements and keep just the main ingredient
        clean_ingredient = re.sub(r'^[\d\s/.-]+', '', ingredient)  # Remove numbers/measurements
        clean_ingredient = re.sub(r'\([^)]*\)', '', clean_ingredient)  # Remove parenthetical notes
        clean_ingredient = clean_ingredient.split(',')[0]  # Take first part before comma
        clean_item = clean_ingredient.strip()
        shopping_list.append(clean_item)
        print(f"  📋 {ingredient} → {clean_item}")
    
    return shopping_list

def extract_cooking_temps_and_times(markdown_text: str) -> Dict:
    """Extract cooking temperatures and times from the recipe"""
    print("\n🌡️ Step 3: Extracting cooking parameters...")
    time.sleep(0.5)
    
    # Extract temperatures
    temp_pattern = r'\$\\mathbf\{(\d+)\}\^\{\\circ\}\s*\\mathbf\{([FC])\}'
    temperatures = re.findall(temp_pattern, markdown_text)
    
    # Extract times
    time_pattern = r'(\d+(?:\s*hour[s]?)?\s*\d*\s*minutes?)'
    times = re.findall(time_pattern, markdown_text, re.IGNORECASE)
    
    temp_list = [f"{temp}°{unit}" for temp, unit in temperatures]
    
    for temp in temp_list:
        print(f"  🌡️  Temperature: {temp}")
    for cooking_time in times:
        print(f"  ⏰ Time: {cooking_time}")
    
    return {
        "temperatures": temp_list,
        "cooking_times": times
    }

def generate_summary(recipe_data: Dict, temps_times: Dict) -> str:
    """Generate a quick summary of the recipe"""
    return f"""
🍽️  Recipe Summary: {recipe_data['title']}
   • {recipe_data['ingredient_count']} ingredients needed
   • {recipe_data['step_count']} cooking steps
   • Cooking temperatures: {', '.join(temps_times['temperatures'])}
   • Estimated times: {', '.join(temps_times['cooking_times'])}
"""

def main():
    print("🎯 DEMO PHASE 2: Smart Recipe Processing")
    print("=" * 60)
    print("Input: Raw Document AI JSON")
    print("Output: Structured recipe data + shopping list\n")
    
    try:
        # Load the Document AI result
        print("📂 Loading Document AI results...")
        doc_result = load_document_ai_result('document_ai_result.json')
        
        # Combine all page content
        full_content = ""
        for page in doc_result['pages']:
            full_content += page['markdown'] + "\n\n"
        
        # Extract structured recipe data
        recipe = extract_recipe_components(full_content)
        temps_times = extract_cooking_temps_and_times(full_content)
        shopping_list = create_shopping_list(recipe)
        
        # Generate summary
        summary = generate_summary(recipe, temps_times)
        
        # Display results with demo flair
        print("\n" + "="*60)
        print("🎉 PROCESSING COMPLETE!")
        print("="*60)
        
        print(summary)
        
        print(f"\n🛒 SHOPPING LIST ({len(shopping_list)} items):")
        print("-" * 30)
        for i, item in enumerate(shopping_list, 1):
            print(f"{i:2}. {item}")
        
        print(f"\n📋 DETAILED INGREDIENTS ({len(recipe['ingredients'])}):")
        print("-" * 30)
        for ingredient in recipe['ingredients']:
            print(f"   • {ingredient}")
        
        print(f"\n👨‍🍳 COOKING STEPS ({len(recipe['instructions'])}):")
        print("-" * 30)
        for i, step in enumerate(recipe['instructions'], 1):
            clean_step = step.replace('\n', ' ').strip()
            preview = clean_step[:80] + "..." if len(clean_step) > 80 else clean_step
            print(f"{i:2}. {preview}")
        
        # Save structured data
        output_data = {
            "recipe": recipe,
            "cooking_info": temps_times,
            "shopping_list": shopping_list,
            "original_pages": len(doc_result['pages']),
            "document_size": doc_result['usage_info']['doc_size_bytes']
        }
        
        with open('structured_recipe_data.json', 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Structured data saved to: structured_recipe_data.json")
        print(f"\n🎯 DEMO COMPLETE! PDF → Shopping List in 2 steps!")
        
    except FileNotFoundError:
        print("❌ Error: document_ai_result.json not found")
        print("▶️  Please run 'python demo-docAIpdf-enhanced.py' first!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()