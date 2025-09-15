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
    print("📄 DEBUG: Analyzing document structure...")
    
    # DEBUG: Show first 500 characters
    print(f"📝 First 500 chars of document:")
    print("-" * 40)
    print(markdown_text[:500])
    print("-" * 40)
    
    time.sleep(0.5)
    
    # Extract title (more flexible)
    title_patterns = [
        r'^# (.+)',  # Standard markdown
        r'^\*\*(.+)\*\*',  # Bold text
        r'^(.+)\n=+',  # Underlined with =
        r'^(.+)\n-+',  # Underlined with -
    ]
    
    title = "Unknown Recipe"
    for pattern in title_patterns:
        title_match = re.search(pattern, markdown_text, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
            break
    
    print(f"📝 Found recipe: {title}")
    
    # Extract ingredients (more flexible patterns)
    ingredients = []
    ingredients_patterns = [
        r'## Ingredients\n\n(.*?)\n\n',  # Current pattern
        r'## Ingredients\n(.*?)\n\n',   # Single newline
        r'# Ingredients\n\n(.*?)\n\n',   # Single #
        r'# Ingredients\n(.*?)\n\n',    # Single # + single newline
        r'\*\*Ingredients\*\*\n\n(.*?)\n\n',  # Bold
        r'\*\*Ingredients\*\*\n(.*?)\n\n',   # Bold + single newline
        r'Ingredients\n\n(.*?)\n\n',     # No header formatting
        r'Ingredients\n(.*?)\n\n',      # No header + single newline
    ]
    
    ingredients_text = ""
    for pattern in ingredients_patterns:
        ingredients_section = re.search(pattern, markdown_text, re.DOTALL)
        if ingredients_section:
            ingredients_text = ingredients_section.group(1)
            print(f"✅ Found ingredients section with pattern: {pattern}")
            break
    
    if ingredients_text:
        print(f"📝 Raw ingredients text:")
        print(ingredients_text[:200] + "..." if len(ingredients_text) > 200 else ingredients_text)
        
        ingredient_lines = ingredients_text.split('\n')
        ingredients = []
        for line in ingredient_lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                clean_ingredient = line.lstrip('- •*').strip()
                if clean_ingredient:
                    ingredients.append(clean_ingredient)
    else:
        print("❌ No ingredients section found")
        # DEBUG: Let's see what sections we do have
        print("🔍 Available sections:")
        sections = re.findall(r'^(#{1,3}.*|.*\n[=-]+)', markdown_text, re.MULTILINE)
        for section in sections[:10]:  # Show first 10 sections
            print(f"  • {section.strip()}")
    
    print(f"🥗 Found {len(ingredients)} ingredients")
    
    # Extract instructions (more flexible patterns)
    instructions = []
    instructions_patterns = [
        r'Instructions\n\n(.*)',      # Current pattern
        r'Instructions\n(.*)',       # Single newline
        r'## Instructions\n\n(.*)',   # With ##
        r'## Instructions\n(.*)',    # With ## + single newline
        r'# Instructions\n\n(.*)',    # With #
        r'# Instructions\n(.*)',     # With # + single newline
        r'\*\*Instructions\*\*\n\n(.*)',  # Bold
        r'\*\*Instructions\*\*\n(.*)',   # Bold + single newline
        r'Directions\n\n(.*)',       # Alternative name
        r'Directions\n(.*)',        # Alternative name + single newline
        r'Method\n\n(.*)',          # Alternative name
        r'Method\n(.*)',           # Alternative name + single newline
    ]
    
    instructions_text = ""
    for pattern in instructions_patterns:
        instructions_match = re.search(pattern, markdown_text, re.DOTALL)
        if instructions_match:
            instructions_text = instructions_match.group(1)
            print(f"✅ Found instructions section with pattern: {pattern}")
            break
    
    if instructions_text:
        print(f"📝 Raw instructions text:")
        print(instructions_text[:200] + "..." if len(instructions_text) > 200 else instructions_text)
        
        # Split by numbered steps
        steps = re.split(r'\n\d+\.\s+', instructions_text)
        instructions = [step.strip() for step in steps if step.strip()]
        
        # If no numbered steps found, try splitting by paragraphs
        if len(instructions) <= 1:
            paragraphs = instructions_text.split('\n\n')
            instructions = [p.strip() for p in paragraphs if p.strip()]
    else:
        print("❌ No instructions section found")
    
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
        if clean_item:  # Only add non-empty items
            shopping_list.append(clean_item)
            print(f"  📋 {ingredient} → {clean_item}")
    
    return shopping_list

def extract_cooking_temps_and_times(markdown_text: str) -> Dict:
    """Extract cooking temperatures and times from the recipe"""
    print("\n🌡️ Step 3: Extracting cooking parameters...")
    time.sleep(0.5)
    
    # Extract temperatures (multiple patterns)
    temp_patterns = [
        r'\$\\mathbf\{(\d+)\}\^\{\\circ\}\s*\\mathbf\{([FC])\}',  # LaTeX format
        r'(\d+)°([FC])',  # Simple format: 425°F
        r'(\d+)\s*degrees?\s*([FC])',  # Text format: 425 degrees F
        r'(\d+)\s*deg\s*([FC])',  # Abbreviated: 425 deg F
    ]
    
    temperatures = []
    for pattern in temp_patterns:
        temps = re.findall(pattern, markdown_text, re.IGNORECASE)
        temperatures.extend(temps)
    
    # Extract times (multiple patterns)
    time_patterns = [
        r'(\d+(?:\s*hour[s]?)?\s*\d*\s*minutes?)',  # Current pattern
        r'(\d+:\d+)',  # Time format: 1:15
        r'(\d+\s*hrs?\s*\d*\s*mins?)',  # Abbreviated: 1 hr 15 mins
        r'(\d+\s*h\s*\d*\s*m)',  # Very abbreviated: 1h 15m
    ]
    
    times = []
    for pattern in time_patterns:
        time_matches = re.findall(pattern, markdown_text, re.IGNORECASE)
        times.extend(time_matches)
    
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
   • Cooking temperatures: {', '.join(temps_times['temperatures']) if temps_times['temperatures'] else 'None detected'}
   • Estimated times: {', '.join(temps_times['cooking_times']) if temps_times['cooking_times'] else 'None detected'}
"""

def main():
    print("🎯 DEMO PHASE 2: Smart Recipe Processing (DEBUG VERSION)")
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
        
        print(f"📄 Total content length: {len(full_content)} characters")
        
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
        print("▶️  Please run 'python demo-docAI.py' or 'python demo-docAIimages.py' first!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()