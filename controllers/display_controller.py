import os
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageCms, ImageOps, ImageEnhance
from luma.core.interface.serial import spi
from luma.lcd.device import ili9486


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class DisplayController:
    """Controller for the Elegoo 3.5" SPI TFT display (ILI9486 via luma.lcd)."""

    # ili9486 in luma.lcd expects native portrait geometry.
    DEFAULT_WIDTH = 320
    DEFAULT_HEIGHT = 480

    def __init__(
        self,
        port: int = 0,
        device: int = 0,
        bus_speed_hz: int = 28000000,
        rotate: int = 1,
        gpio_dc: int = 24,
        gpio_rst: int = 25,
    ):
        self.port = int(os.getenv("LOVEBOX_DISPLAY_SPI_PORT", port))
        self.device = int(os.getenv("LOVEBOX_DISPLAY_SPI_DEVICE", device))
        self.bus_speed_hz = int(os.getenv("LOVEBOX_DISPLAY_BUS_SPEED_HZ", bus_speed_hz))
        self.rotate = int(os.getenv("LOVEBOX_DISPLAY_ROTATE", rotate))
        self.gpio_dc = int(os.getenv("LOVEBOX_DISPLAY_GPIO_DC", gpio_dc))
        self.gpio_rst = int(os.getenv("LOVEBOX_DISPLAY_GPIO_RST", gpio_rst))
        # Some ILI9486 HAT variants are wired as color-inverted.
        self.invert_output = _env_bool("LOVEBOX_DISPLAY_INVERT_OUTPUT", True)
        self.use_bgr = _env_bool("LOVEBOX_DISPLAY_BGR", False)
        self.color_manage = _env_bool("LOVEBOX_DISPLAY_COLOR_MANAGE", True)

        serial = spi(
            port=self.port,
            device=self.device,
            gpio_DC=self.gpio_dc,
            gpio_RST=self.gpio_rst,
            bus_speed_hz=self.bus_speed_hz,
            # mode = 2
        )
        self._lcd = ili9486(
            serial,
            width=self.DEFAULT_WIDTH,
            height=self.DEFAULT_HEIGHT,
            rotate=self.rotate,
            bgr=self.use_bgr,
            # invert=False,
        )

    @property
    def size(self):
        return self._lcd.size

    def _to_srgb_if_profiled(self, image: Image.Image) -> Image.Image:
        icc_profile = image.info.get("icc_profile")
        if not icc_profile:
            return image

        src_profile = ImageCms.ImageCmsProfile(BytesIO(icc_profile))
        dst_profile = ImageCms.createProfile("sRGB")
        output_mode = image.mode if image.mode in ("RGB", "RGBA") else "RGB"
        return ImageCms.profileToProfile(
            image,
            src_profile,
            dst_profile,
            outputMode=output_mode,
        )

    def _prepare_frame(self, image: Image.Image) -> Image.Image:
        # 1. Fix orientation
        frame = ImageOps.exif_transpose(image)

        # 2. Fix "weird colors": Convert phone color profiles (like Display P3) to sRGB
        if self.color_manage:
            frame = self._to_srgb_if_profiled(frame)

        # 3. Resize and crop
        if frame.size != self.size:
            frame = ImageOps.fit(frame, self.size, method=Image.Resampling.BICUBIC)

        # 4. Ensure RGB format
        if frame.mode != "RGB":
            frame = frame.convert("RGB")

        # 5. Fix "blown out" look: Compensate for the TFT's washed-out gamma
        # Reduce brightness to pull back blown-out highlights
        frame = ImageEnhance.Brightness(frame).enhance(0.85) 
        
        # Boost contrast to restore depth
        frame = ImageEnhance.Contrast(frame).enhance(1.15)
        
        # Slightly boost saturation to combat the dull TFT screen
        frame = ImageEnhance.Color(frame).enhance(1.10)

        # 6. Hardware specific inversion
        if self.invert_output:
            frame = ImageOps.invert(frame)
            
        return frame

    def display_image(self, image_path: str):
        image_file = Path(image_path)
        if not image_file.exists():
            raise FileNotFoundError(f"Image file does not exist: {image_file}")

        with Image.open(image_file) as image:
            self._lcd.display(self._prepare_frame(image))

    def set_black(self):
        black = Image.new("RGB", self.size, "black")
        self._lcd.display(self._prepare_frame(black))
