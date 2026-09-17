"""Genera icon.ico: un cuadrado redondeado con degradado azul->morado,
un triangulo de "play" blanco (avanzar/iniciar) y un punto rojo (laser)."""

from PIL import Image, ImageDraw, ImageFilter

SIZE = 256


def make_gradient(size, c1, c2):
    grad = Image.new("RGB", (1, size), color=0)
    for y in range(size):
        t = y / (size - 1)
        r = round(c1[0] + (c2[0] - c1[0]) * t)
        g = round(c1[1] + (c2[1] - c1[1]) * t)
        b = round(c1[2] + (c2[2] - c1[2]) * t)
        grad.putpixel((0, y), (r, g, b))
    diag = grad.resize((size, size)).convert("RGBA")
    return diag.rotate(45, resample=Image.BICUBIC, expand=False, fillcolor=(0, 0, 0, 0))


def rounded_mask(size, radius):
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

# fondo con sombra suave
shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
sd = ImageDraw.Draw(shadow)
sd.rounded_rectangle([14, 18, SIZE - 14, SIZE - 10], radius=58, fill=(20, 20, 30, 120))
shadow = shadow.filter(ImageFilter.GaussianBlur(8))
canvas.alpha_composite(shadow)

bg = make_gradient(SIZE, (37, 99, 235), (124, 58, 237)).convert("RGBA")
mask = rounded_mask(SIZE, 58)
rounded_bg = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
rounded_bg.paste(bg, (0, 0), mask)
canvas.alpha_composite(rounded_bg)

# leve brillo superior
gloss = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
gd = ImageDraw.Draw(gloss)
gd.rounded_rectangle([10, 10, SIZE - 10, SIZE * 0.55], radius=48, fill=(255, 255, 255, 28))
gloss_mask = rounded_mask(SIZE, 58)
gloss_masked = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
gloss_masked.paste(gloss, (0, 0), gloss_mask)
canvas.alpha_composite(gloss_masked)

draw = ImageDraw.Draw(canvas)

# triangulo "play" blanco, ligeramente a la izquierda de centro
cx, cy = SIZE * 0.44, SIZE * 0.52
tri_w, tri_h = SIZE * 0.30, SIZE * 0.34
triangle = [
    (cx - tri_w * 0.4, cy - tri_h / 2),
    (cx - tri_w * 0.4, cy + tri_h / 2),
    (cx + tri_w * 0.6, cy),
]
shadow_tri = [(x + 3, y + 4) for x, y in triangle]
draw.polygon(shadow_tri, fill=(20, 20, 40, 70))
draw.polygon(triangle, fill=(255, 255, 255, 235))

# punto laser rojo arriba a la derecha del triangulo, con halo
laser_x, laser_y = SIZE * 0.72, SIZE * 0.30
for r, alpha in [(34, 45), (24, 90), (15, 255)]:
    color = (255, 40, 40, alpha) if alpha < 255 else (255, 45, 45, 255)
    draw.ellipse(
        [laser_x - r, laser_y - r, laser_x + r, laser_y + r],
        fill=color,
    )
draw.ellipse(
    [laser_x - 6, laser_y - 6, laser_x + 2, laser_y + 2],
    fill=(255, 220, 220, 200),
)

sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
canvas.save(r"C:\Users\avb08\Desktop\RemoteControl\icon.ico", sizes=sizes)
print("icon.ico generado")
