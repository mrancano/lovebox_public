import os
import asyncio
import glob
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from controllers.servo_controller import ServoController
from controllers.display_controller import DisplayController
from controllers.audio_controller import convert_to_wav
from controllers.text_to_png import text_to_png

try:
    from gpiozero import Button
except ImportError:
    # Fallback for testing environments without gpiozero
    Button = None
    print("gpiozero not found. Button functionality will be disabled.")

# Directory to save incoming media
DOWNLOAD_DIR = "/home/mrancano/telegram_media"
BUTTON_PIN = 3

load_dotenv()

TELEGRAM_KEY = os.getenv("TELEGRAM_KEY")
MY_CHAT_ID = os.getenv("MY_CHAT_ID")

print(f"Loaded TELEGRAM_KEY: {'set' if TELEGRAM_KEY else 'NOT SET'}"
      f" and MY_CHAT_ID: {MY_CHAT_ID}"
      )


# Shared application state
class AppState:
    def __init__(self):
        self.active_task = None
        self.last_chat_id = None
        self.main_loop = None
        self.servo = None
        self.display = None
        self.current_media_path = None
state = AppState()
application = None

async def capture_loop(app: Application):
    """Post-init hook to capture the running event loop for the GPIO thread."""
    state.main_loop = asyncio.get_running_loop()

def cleanup_media():
    """Centralized cleanup function for media files."""
    print("Cleaning up media files...")
    files = glob.glob(os.path.join(DOWNLOAD_DIR, "*"))
    for f in files:
        if os.path.isfile(f):
            try:
                os.remove(f)
            except Exception as e:
                print(f"Error deleting file {f}: {e}")

async def process_message(kind: str, argument_data: str):
    """The async task that replaces on_message.py"""
    try:
        print(f"Target program started. Processing {kind}...")
        state.servo.go_to_degrees(180)
        if kind == "text":
            print(f"The text says: {argument_data}")
            # Simulate some long-running work
            text_image_path = text_to_png(argument_data)
            if state.display:
                state.display.display_image(text_image_path)
            await asyncio.sleep(5)
        elif kind == "video":
            print(f"Processing file located at: {argument_data}")
            # Simulate some long-running work
            await asyncio.sleep(5)
        elif kind in ["audio", "voice"]:
            print(f"Playing audio located at: {state.current_media_path}")
                        
            # Run aplay asynchronously
            process = await asyncio.create_subprocess_exec(
                "aplay", state.current_media_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            
            # Await the process to finish playing the audio
            await process.communicate()
            
            if process.returncode == 0:
                print("Audio playback finished successfully.")
            else:
                print(f"Failed to play audio at {state.current_media_path}. Check aplay logs.")
        elif kind == "photo":
            print(f"Displaying photo located at: {argument_data}")
            if state.display:
                state.display.display_image(argument_data)
                state.display.display_image(argument_data)
            # Simulate some long-running work
            await asyncio.sleep(5)

        
        print("Processing finished cleanly.")
    except asyncio.CancelledError:
        if state.audio:
            state.audio.stop()
        print("Processing task was CANCELLED.")
        raise
    finally:
        state.servo.go_to_degrees(0)
        state.display.set_black()
        cleanup_media()
        state.active_task = None
        print("State reset to idle.")

async def trigger_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ignore new messages if we are currently processing one
    if state.active_task is not None and not state.active_task.done():
        print("Busy processing a message. Ignoring new message.")
        return

    message = update.message
    state.last_chat_id = message.chat_id
    kind = "unknown"
    argument_data = ""

    # 1. Handle Text
    if message.text:
        kind = "text"
        argument_data = message.text

    # 2. Handle Photos
    elif message.photo:
        kind = "photo"
        file_id = message.photo[-1].file_id
        new_file = await context.bot.get_file(file_id)
        filepath = os.path.join(DOWNLOAD_DIR, f"{file_id}.jpg")
        await new_file.download_to_drive(filepath)
        argument_data = filepath

    # 2b. Handle image documents (non-recompressed original files)
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("image/"):
        kind = "photo"
        file_id = message.document.file_id
        new_file = await context.bot.get_file(file_id)
        file_suffix = Path(message.document.file_name or "").suffix or ".img"
        filepath = os.path.join(DOWNLOAD_DIR, f"{file_id}{file_suffix}")
        await new_file.download_to_drive(filepath)
        argument_data = filepath

    # 3. Handle Videos
    elif message.video:
        kind = "video"
        file_id = message.video.file_id
        new_file = await context.bot.get_file(file_id)
        filepath = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp4")
        await new_file.download_to_drive(filepath)
        argument_data = filepath

# 4. Handle Audio Notes
    elif message.audio:
        kind = "audio"
        file_id = message.audio.file_id
        new_file = await context.bot.get_file(file_id)
        
        file_suffix = Path(message.audio.file_name or "").suffix
        if not file_suffix and message.audio.mime_type:
            file_suffix = f".{message.audio.mime_type.split('/')[-1]}"
            
        filepath = os.path.join(DOWNLOAD_DIR, f"{file_id}{file_suffix or '.audio'}")
        await new_file.download_to_drive(filepath)
        
        # Convert downloaded file to WAV
        wav_filepath = await convert_to_wav(filepath)
        
        state.current_media_path = wav_filepath
        argument_data = wav_filepath

    # 5. Handle Voice Notes
    elif message.voice:
        kind = "voice"
        file_id = message.voice.file_id
        new_file = await context.bot.get_file(file_id)
        
        filepath = os.path.join(DOWNLOAD_DIR, f"{file_id}.ogg")
        await new_file.download_to_drive(filepath)
        
        # Convert downloaded file to WAV
        wav_filepath = await convert_to_wav(filepath)
        
        state.current_media_path = wav_filepath
        argument_data = wav_filepath

    print(f"Message type: {kind} received. Kickstarting internal task...")
    
    if kind != "unknown":
        # Launch as an async task instead of a subprocess
        state.active_task = asyncio.create_task(process_message(kind, argument_data))

def button_callback():
    """GPIO callback for button press."""
    print("Button pressed!")
    # Schedule work in the asyncio event loop safely
    if state.main_loop and state.main_loop.is_running():
        asyncio.run_coroutine_threadsafe(handle_button_press(), state.main_loop)

async def handle_button_press():
    if state.active_task is not None and not state.active_task.done():
        print("Cancelling active task...")
        state.active_task.cancel()
        # cleanup_media will be called in the finally block of process_message
    else:
        print("Button pressed while idle.")
        if application and application.bot:
            try:
                print("Sending ❤️ to the last chat...")
                state.servo.go_to_degrees(180)
                await application.bot.send_message(chat_id=MY_CHAT_ID, text="❤️")
                state.servo.go_to_degrees(0)
                print(f"Message sent successfully to :{MY_CHAT_ID}")
            except Exception as e:
                print(f"Failed to send message: {e}")

# Keep a reference to prevent garbage collection
hardware_button = None

def setup_gpio():
    global hardware_button
    if Button is not None:
        # GPIO 2 and 3 on the Raspberry Pi have fixed physical pull-up resistors on the board.
        # gpiozero enforces this by requiring pull_up=True for these pins.
        hardware_button = Button(BUTTON_PIN, pull_up=True, bounce_time=0.2)
        hardware_button.when_pressed = button_callback
    if ServoController is not None:
        state.servo = ServoController()
    if DisplayController is not None:
        state.display = DisplayController()
        state.display.set_black()
    else:
        print("Warning: gpiozero not found. Mocking button functionality.")

def main():
    global application
    
    # Ensure the download directory exists
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    cleanup_media() # Clean up any existing media on startup

    setup_gpio()

    # Replace 'YOUR_BOT_TOKEN' with your actual token
    application = Application.builder().token(TELEGRAM_KEY).post_init(capture_loop).build()

    # Create a filter that accepts Text, Photos, image Documents, Videos, and Voice messages
    media_filter = (
        filters.TEXT
        | filters.PHOTO
        | filters.Document.IMAGE
        | filters.VIDEO
        | filters.AUDIO
        | filters.VOICE
    )

    # Listen for those specific types
    application.add_handler(MessageHandler(media_filter, trigger_program))

    print("Listening for Telegram text and media...")
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    finally:
        if hardware_button is not None:
            hardware_button.close()
        cleanup_media()

if __name__ == "__main__":
    main()
