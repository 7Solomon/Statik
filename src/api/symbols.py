from flask import Blueprint, send_file, jsonify, request
import io
from PIL import Image, ImageDraw
from src.plugins.generator.image.stanli_symbols import (
    StanliSupport, StanliHinge,
    SupportType, HingeType,
)

bp = Blueprint('symbols', __name__, url_prefix='/symbols')

SYMBOL_METADATA = {
    'festlager': {
        'category': 'support',
        'fix_x': True, 'fix_y': True, 'fix_m': False,
        'anchor': [50.0, 30.0],
        'class': StanliSupport, 'enum': SupportType.FESTLAGER
    },
    'loslager': {
        'category': 'support',
        'fix_x': False, 'fix_y': True, 'fix_m': False,
        'anchor': [50.0, 30.0],
        'class': StanliSupport, 'enum': SupportType.LOSLAGER
    },
    'einspannung': {
        'category': 'support',
        'fix_x': True, 'fix_y': True, 'fix_m': True,
        'anchor': [50.0, 30.0],
        'class': StanliSupport, 'enum': SupportType.FESTE_EINSPANNUNG
    },
    'gleitlager': {
        'category': 'support',
        'fix_x': True, 'fix_y': False, 'fix_m': True,
        'anchor': [50.0, 30.0],
        'class': StanliSupport, 'enum': SupportType.GLEITLAGER
    },
    'vollgelenk': {
        'category': 'hinge',
        'releases_m': True, # Hint for member end
        'anchor': [50.0, 50.0],
        'class': StanliHinge, 'enum': HingeType.VOLLGELENK
    }
}

@bp.get('/definitions')
def get_definitions():
    """
    Returns the physics/logic definition for the frontend.
    The frontend is now 'dumb' and just stores these values.
    """
    # Filter out the internal python classes before sending JSON
    client_data = {}
    for key, data in SYMBOL_METADATA.items():
        client_data[key] = {
            'category': data['category'],
            'fix_x': data.get('fix_x', False),
            'fix_y': data.get('fix_y', False),
            'fix_m': data.get('fix_m', False),
            'anchor': data['anchor']
        }
    return jsonify(client_data)

@bp.get('/get/<name>')
def get_symbol_image(name):
    """
    Generates and returns the PNG for a symbol.
    """
    name = name.lower()
    rotation_deg = request.args.get('rotation', default=0, type=float)
    
    if name not in SYMBOL_METADATA:
        return jsonify({"error": f"Unknown symbol: {name}"}), 404
    
    try:
        data = SYMBOL_METADATA[name]
        ClassType = data['class']
        EnumValue = data['enum']
        center_pos = tuple(data['anchor'])

        # Create Image
        img = Image.new('RGBA', (100, 100), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)

        # Draw Symbol
        symbol = ClassType(EnumValue)
        
        # Apply rotation logic
        if ClassType == StanliSupport:
            symbol.draw(draw, center_pos, rotation=rotation_deg)
        else:
            symbol.draw(draw, center_pos)

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        
        return send_file(buf, mimetype='image/png')
    except Exception as e:
        return jsonify({"error": str(e)}), 500