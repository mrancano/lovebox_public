import itertools
import time
from pathlib import Path

from PIL import Image, ImageOps
from luma.core.interface.serial import spi
from luma.lcd.device import ili9486


SPI_PORT = 0
SPI_DEVICE = 0
GPIO_DC = 24
GPIO_RST = 25
ROTATE = 1
DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 480
TEST_DURATION_SECONDS = 10
BUS_SPEEDS_MHZ = [ 32]
BGR_OPTIONS = [False]
PREPROCESS_OPTIONS = [False]


def get_first_test_image() -> Path:
    images_dir = Path(__file__).resolve().parent / "test_images"
    candidates = sorted(
        p for p in images_dir.iterdir() if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}
    )
    if not candidates:
        raise FileNotFoundError(f"No test images found in: {images_dir}")
    return candidates[0]


def build_device(bus_speed_hz: int, bgr: bool):
    serial = spi(
        port=SPI_PORT,
        device=SPI_DEVICE,
        gpio_DC=GPIO_DC,
        gpio_RST=GPIO_RST,
        bus_speed_hz=bus_speed_hz,
    )
    return ili9486(
        serial,
        width=DISPLAY_WIDTH,
        height=DISPLAY_HEIGHT,
        rotate=ROTATE,
        bgr=bgr,
        invert=False
    )


def prepare_image(image: Image.Image, target_size: tuple[int, int], preprocess: bool) -> Image.Image:
    if preprocess:
        return ImageOps.invert(image)
    return image


def main():
    image_path = get_first_test_image()
    combinations = list(itertools.product(BUS_SPEEDS_MHZ, BGR_OPTIONS, PREPROCESS_OPTIONS))
    total = len(combinations)

    print("=" * 80)
    print("DISPLAY QUALITY SWEEP")
    print(f"Image: {image_path.name}")
    print(f"Total iterations: {total}")
    print(f"Display time per iteration: {TEST_DURATION_SECONDS}s")
    print("=" * 80)

    for index, (speed_mhz, bgr, preprocess) in enumerate(combinations, start=1):
        speed_hz = speed_mhz * 1_000_000
        print(
            f"[{index:02d}/{total:02d}] "
            f"bus={speed_mhz:>2}MHz | color_order={'BGR' if bgr else 'RGB'} | preprocess={preprocess}"
        )

        lcd = build_device(bus_speed_hz=speed_hz, bgr=bgr)
        with Image.open(image_path) as image:
            frame = prepare_image(image=image, target_size=lcd.size, preprocess=preprocess)
            lcd.display(frame)

        time.sleep(TEST_DURATION_SECONDS)

    final_device = build_device(bus_speed_hz=4_000_000, bgr=True)
    final_device.display(Image.new("RGB", final_device.size, "black"))
    print("=" * 80)
    print("Sweep complete. Display set to black.")
    print("=" * 80)


if __name__ == "__main__":
    main()
