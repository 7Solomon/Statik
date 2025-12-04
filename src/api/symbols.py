from flask import Blueprint, send_file, jsonify
import io
from PIL import Image, ImageDraw
from src.generator.image.stanli_symbols import (
    StanliSupport, StanliHinge,
    SupportType, HingeType,
)

bp = Blueprint('symbols', __name__, url_prefix='/symbols')

SYMBOL_MAP = {
    # Supports
    'festlager': (StanliSupport, SupportType.FESTLAGER, (50.0, 30.0)),
    'loslager': (StanliSupport, SupportType.LOSLAGER, (50.0, 30.0)),
    'einspannung': (StanliSupport, SupportType.FESTE_EINSPANNUNG, (50.0, 30.0)),
    'gleitlager': (StanliSupport, SupportType.GLEITLAGER, (50.0, 30.0)),
    'feder': (StanliSupport, SupportType.FEDER, (50.0, 30.0)),
    'torsionsfeder': (StanliSupport, SupportType.TORSIONSFEDER, (50.0, 30.0)),
    
    # Hinges
    'vollgelenk': (StanliHinge, HingeType.VOLLGELENK, (50.0, 50.0)),
    'halbgelenk': (StanliHinge, HingeType.HALBGELENK, (50.0, 50.0)),
    'schubgelenk': (StanliHinge, HingeType.SCHUBGELENK, (50.0, 50.0)),
}

@bp.route('/get/<name>', methods=['GET'])
def get_symbol_image(name):
    name = name.lower()
    
    if name not in SYMBOL_MAP:
        return jsonify({"error": f"Unknown symbol: {name}"}), 404
    
    try:
        # Unpack config
        ClassType, EnumValue, center_pos = SYMBOL_MAP[name]

        # Create Image
        img = Image.new('RGBA', (100, 100), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)

        # Draw Symbol
        symbol = ClassType(EnumValue)
        
        # Supports take extra rotation arg, Hinges don't need it but can take it
        if ClassType == StanliSupport:
            symbol.draw(draw, center_pos, rotation=0)
        else:
            symbol.draw(draw, center_pos)

        # Return PNG
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        
        return send_file(buf, mimetype='image/png')
    except Exception as e:
        return jsonify({"error": str(e)}), 500
