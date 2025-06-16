from django.core.exceptions import ValidationError
from PIL import Image

def validate_image_size(image):
    limit = 5
    if image.size >= limit * 1024 * 1024:
        raise ValidationError(f"The image size must not exceed {limit}MB.")

def validate_image_resolution(image):
    min_width, min_height = 400, 300
    max_width, max_height = 4000, 4000
    img = Image.open(image)
    width, height = img.size

    if width > max_width or height > max_height:
        raise ValidationError("Maximum allowed resolution is 4000x4000 pixels.")
    if width < min_width or height < min_height:
        raise ValidationError("Minimum allowed resolution is 400x300 pixels.")
