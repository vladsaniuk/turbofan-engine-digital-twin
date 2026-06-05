def get_color(score: float) -> str:
    # Normalize score. Typical scores range from 0 to ~0.05. We cap at 0.05 for max red.
    norm = min(score / 0.02, 1.0)
    if norm < 0.5:
        # Green to Amber
        t = norm * 2
        r = int(44 + t * (255 - 44))
        g = int(160 + t * (191 - 160))
        b = int(44 + t * (0 - 44))
    else:
        # Amber to Red
        t = (norm - 0.5) * 2
        r = int(255 + t * (214 - 255))
        g = int(191 + t * (39 - 191))
        b = int(0 + t * (40 - 0))
    return f"rgb({r},{g},{b})"

def render_engine_svg(subsystem_scores: dict) -> str:
    blocks = [
        {"name": "Fan", "x": 50, "y": 20, "w": 100, "h": 260},
        {"name": "LPC", "x": 155, "y": 60, "w": 90, "h": 180},
        {"name": "HPC", "x": 250, "y": 90, "w": 110, "h": 120},
        {"name": "Combustor", "x": 365, "y": 90, "w": 70, "h": 120},
        {"name": "HPT", "x": 440, "y": 70, "w": 90, "h": 160},
        {"name": "LPT", "x": 535, "y": 40, "w": 140, "h": 220},
    ]
    
    svg = ['<svg viewBox="0 0 750 300" width="100%" height="300" xmlns="http://www.w3.org/2000/svg">']
    
    # Outer casing lines to suggest engine shape
    svg.append('<path d="M 30,10 L 720,30 L 720,270 L 30,290 Z" fill="#e0e0e0" stroke="#999" stroke-width="2"/>')
    # Center shaft
    svg.append('<rect x="20" y="140" width="710" height="20" fill="#888"/>')
    
    for b in blocks:
        name = b["name"]
        score = subsystem_scores.get(name, 0.0)
        color = get_color(score)
        
        svg.append(f'<rect x="{b["x"]}" y="{b["y"]}" width="{b["w"]}" height="{b["h"]}" fill="{color}" stroke="#333" stroke-width="2" rx="8"/>')
        
        # Center text
        cx = b["x"] + b["w"] / 2
        cy = b["y"] + b["h"] / 2
        # Text shadow for readability
        svg.append(f'<text x="{cx}" y="{cy - 5}" font-family="sans-serif" font-size="18" font-weight="bold" fill="#fff" stroke="#000" stroke-width="3" paint-order="stroke" text-anchor="middle">{name}</text>')
        svg.append(f'<text x="{cx}" y="{cy + 15}" font-family="sans-serif" font-size="14" fill="#fff" stroke="#000" stroke-width="2" paint-order="stroke" text-anchor="middle">{score:.4f}</text>')
        
    svg.append('</svg>')
    return "\n".join(svg)
