from PIL import Image
import utils


def test_draw():
    # Create a white image
    img = Image.new("RGB", (1000, 1000), "white")

    # Bbox from user data: [192, 192, 209, 485] (normalized 0-1000)
    bbox = [192, 192, 209, 485]

    # Draw
    img_drawn = utils.draw_bounding_box(img, bbox, label="Test", color="red")

    # Save
    img_drawn.save("test_bbox.png")
    print("Saved test_bbox.png")


if __name__ == "__main__":
    test_draw()
