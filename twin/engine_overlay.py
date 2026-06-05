import os
import base64
from twin.engine_svg import get_color

# CONSTANTS - Tweak these percentages to match your actual cutaway image
# Format: {"subsystem": {"left": %, "top": %, "width": %, "height": %}}
# Note: These need visual tuning to the chosen image!
ZONES = {
    "Fan": {"left": 5, "top": 15, "width": 12, "height": 70},
    "LPC": {"left": 18, "top": 28, "width": 15, "height": 44},
    "HPC": {"left": 34, "top": 35, "width": 7, "height": 30},
    "Combustor": {"left": 42, "top": 35, "width": 9, "height": 30},
    "HPT": {"left": 52, "top": 35, "width": 7, "height": 30},
    "LPT": {"left": 60, "top": 25, "width": 13, "height": 50},
}

def render_engine_overlay(subsystem_scores: dict, image_path: str = "assets/engine_diagram.png") -> str:
    """Renders HTML with base engine image and subsystem health overlays."""
    # Check if image exists and is valid
    if not os.path.exists(image_path) or os.path.getsize(image_path) < 100:
        alt_path = image_path.replace(".png", ".svg")
        if os.path.exists(alt_path) and os.path.getsize(alt_path) > 100:
            image_path = alt_path
        else:
            return None  # Fallback to Tier 1
        
    with open(image_path, "rb") as img_file:
        img_b64 = base64.b64encode(img_file.read()).decode()
    
    # Determine mime type from extension
    ext = os.path.splitext(image_path)[1].lower()
    mime = "image/png"
    if ext in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
    elif ext == ".svg":
        mime = "image/svg+xml"
        
    img_data_url = f"data:{mime};base64,{img_b64}"
    
    html = [
        f'<div style="position: relative; width: 100%; max-width: 800px; margin: 0 auto;">',
        f'  <img src="{img_data_url}" style="width: 100%; height: auto; display: block; border-radius: 8px; border: 1px solid #ccc; background-color: white;"/>'
    ]
    
    for sub, pos in ZONES.items():
        score = subsystem_scores.get(sub, 0.0)
        # Re-use get_color, but append transparency
        rgb_str = get_color(score)
        # get_color returns "rgb(r,g,b)". We want "rgba(r,g,b,0.45)"
        rgba_str = rgb_str.replace("rgb(", "rgba(").replace(")", ", 0.45)")
        
        left = pos["left"]
        top = pos["top"]
        width = pos["width"]
        height = pos["height"]
        
        html.append(f'''
        <div style="position: absolute; left: {left}%; top: {top}%; width: {width}%; height: {height}%; 
                    background-color: {rgba_str}; border: 1px dashed rgba(0,0,0,0.5); border-radius: 4px;
                    display: flex; align-items: center; justify-content: center; flex-direction: column;">
            <span style="background: rgba(255,255,255,0.8); padding: 2px 4px; border-radius: 3px; font-weight: bold; font-size: 12px; color: #000; font-family: sans-serif;">{sub}</span>
            <span style="background: rgba(255,255,255,0.8); padding: 2px 4px; border-radius: 3px; font-size: 10px; color: #000; font-family: sans-serif; margin-top: 2px;">{(score):.4f}</span>
        </div>
        ''')
        
    html.append('</div>')
    return "\n".join(html)
