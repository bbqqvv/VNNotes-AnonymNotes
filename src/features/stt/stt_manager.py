import logging
import os
import tempfile
import threading
import time
from PyQt6.QtCore import QObject, pyqtSignal, QUrl, QTimer
from PyQt6.QtMultimedia import QMediaCaptureSession, QAudioInput, QMediaRecorder, QMediaFormat

logger = logging.getLogger(__name__)

class STTManager(QObject):
    """
    Real-time "feel" STT using Continuous Piecewise recording.
    Records chunks of audio and processes them sequentially.
    """
    transcription_received = pyqtSignal(str)
    interim_received = pyqtSignal(str) # For backward compatibility in UI
    state_changed = pyqtSignal(str) 

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. Setup Audio Input & Session
        self.audio_input = QAudioInput()
        self.capture_session = QMediaCaptureSession()
        self.capture_session.setAudioInput(self.audio_input)
        
        # 2. Setup Recorder
        self.recorder = QMediaRecorder()
        self.capture_session.setRecorder(self.recorder)
        
        # Configuration (16kHz Mono WAV)
        media_format = QMediaFormat()
        media_format.setFileFormat(QMediaFormat.FileFormat.Wave)
        media_format.setAudioCodec(QMediaFormat.AudioCodec.Wave)
        self.recorder.setMediaFormat(media_format)
        self.recorder.setAudioSampleRate(16000)
        self.recorder.setAudioChannelCount(1)
        self.recorder.setQuality(QMediaRecorder.Quality.HighQuality)
        
        # 3. State Management
        self.recorder.recorderStateChanged.connect(self._on_recorder_state_changed)
        self.recorder.errorOccurred.connect(self._on_recorder_error)
        
        self._is_active = False
        self._current_lang = 'vi-VN'
        self._chunk_timer = QTimer(self)
        self._chunk_timer.timeout.connect(self._rotate_chunk)
        self._current_chunk_path = None
        self._chunk_duration_ms = 4000 # 4 seconds per update for "real-time" feel

    def _on_recorder_state_changed(self, state):
        if state == QMediaRecorder.RecorderState.RecordingState:
            self.state_changed.emit("recording")
        elif state == QMediaRecorder.RecorderState.StoppedState:
            if self._is_active:
                # Process the chunk we just finished
                path_to_process = self._current_chunk_path
                if path_to_process and os.path.exists(path_to_process):
                    threading.Thread(target=self._worker_process, args=(path_to_process,), daemon=True).start()
                
                # Immediately start next if still active
                if self._is_active:
                    self._start_new_chunk()

    def _on_recorder_error(self, error, error_str):
        logger.error(f"STT Recorder Error: {error_str}")
        self.state_changed.emit(f"error: {error_str}")

    def start(self, lang='vi-VN'):
        """Starts the continuous recording loop."""
        self._current_lang = lang
        self._is_active = True
        self._start_new_chunk()
        self._chunk_timer.start(self._chunk_duration_ms)
        logger.info("STT: Continuous recording started")

    def stop(self):
        """Stops the loop."""
        self._is_active = False
        self._chunk_timer.stop()
        if self.recorder.recorderState() == QMediaRecorder.RecorderState.RecordingState:
            self.recorder.stop()
        self.state_changed.emit("stopped")

    def toggle(self, lang='vi-VN'):
        if self._is_active: self.stop()
        else: self.start(lang)

    def _start_new_chunk(self):
        """Starts a new recording chunk."""
        self._current_chunk_path = os.path.join(tempfile.gettempdir(), f"stt_chunk_{int(time.time()*1000)}.wav")
        self.recorder.setOutputLocation(QUrl.fromLocalFile(self._current_chunk_path))
        self.recorder.record()

    def _rotate_chunk(self):
        """Triggers a stop to finish current chunk and start next one."""
        if self._is_active:
            self.recorder.stop()

    def _worker_process(self, file_path):
        """Transcribes a single audio chunk."""
        try:
            # Short sleep to ensure file is flushed by OS
            time.sleep(0.3)
            
            import speech_recognition as sr
            r = sr.Recognizer()
            
            with sr.AudioFile(file_path) as source:
                audio = r.record(source)
            
            text = r.recognize_google(audio, language=self._current_lang)
            if text:
                logger.info(f"STT Chunk: {text}")
                self.transcription_received.emit(text)
                
        except Exception as e:
            # Silent on chunk errors (usually silence or noise)
            logger.debug(f"STT Chunk Skip: {e}")
        finally:
            # Cleanup chunk file
            if file_path and os.path.exists(file_path):
                try: os.remove(file_path)
                except: pass
