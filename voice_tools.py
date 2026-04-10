import whisper
from pydub import AudioSegment

model = whisper.load_model("base")

def transcribe_voice(file_path):
    audio = AudioSegment.from_file(file_path)
    wav_path = file_path.replace(".ogg", ".wav")
    audio.export(wav_path, format="wav")

    result = model.transcribe(wav_path, language="he")
    return result["text"].lower()
