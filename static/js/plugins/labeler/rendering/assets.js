const SYMBOL_CACHE = {};

export function getSymbolImage(name, rotation, onLoaded) {
    const r = Math.round(rotation * 100) / 100;
    const key = `${name}_${r}`;

    if (SYMBOL_CACHE[key] && SYMBOL_CACHE[key].complete) {
        return SYMBOL_CACHE[key];
    }

    const img = new Image();
    img.onload = () => {
        if (onLoaded) onLoaded();
        if (window.triggerRender) window.triggerRender();
    };

    img.src = `/symbols/get/${name}?rotation=${r}`;
    SYMBOL_CACHE[key] = img;
    return img;
}
