import time
from pathlib import Path

from controllers.display_controller import DisplayController


TEST_IMAGE_NAME = "660 Crescentia (A908 AN)_A_annotated.png"


def main():
    project_root = Path(__file__).resolve().parents[1]
    image_path = project_root / TEST_IMAGE_NAME

    display = DisplayController()
    display.display_image(str(image_path))
    print(f"Displayed image: {image_path}")

    time.sleep(5)
    display.set_black()
    print("Display set to black.")


if __name__ == "__main__":
    main()
