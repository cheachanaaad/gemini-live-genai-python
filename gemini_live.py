import asyncio
import inspect
import json
import logging

logger = logging.getLogger(__name__)
from google import genai
from google.genai import types

class GeminiLive:
    """
    Handles the interaction with the Gemini Live API.
    """
    def __init__(
        self,
        api_key,
        model,
        input_sample_rate,
        tools=None,
        tool_mapping=None,
        system_instruction=None,
    ):
        """
        Initializes the GeminiLive client.

        Args:
            api_key (str): The Gemini API Key.
            model (str): The model name to use.
            input_sample_rate (int): The sample rate for audio input.
            tools (list, optional): List of tools to enable. Defaults to None.
            tool_mapping (dict, optional): Mapping of tool names to functions. Defaults to None.
        """
        self.api_key = api_key
        self.model = model
        self.input_sample_rate = input_sample_rate
        self.client = genai.Client(
            api_key=api_key, http_options={"api_version": "v1alpha"}
        )
        self.tools = tools or []
        self.tool_mapping = tool_mapping or {}
        self.system_instruction = system_instruction or (
            "You are a helpful AI assistant. Keep your responses concise."
        )
        logger.info(
            "GeminiLive initialized model=%s tools=%s",
            self.model,
            [
                getattr(declaration, "name", "<unknown>")
                for tool in self.tools
                for declaration in getattr(tool, "function_declarations", [])
            ],
        )

    async def start_session(self, audio_input_queue, video_input_queue, text_input_queue, audio_output_callback, audio_interrupt_callback=None):
        logger.info(
            "Starting Gemini Live session model=%s input_sample_rate=%s",
            self.model,
            self.input_sample_rate,
        )
        config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Puck"
                    )
                )
            ),
            system_instruction=types.Content(
                parts=[types.Part(text=self.system_instruction)]
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            tools=self.tools,
        )
        
        async with self.client.aio.live.connect(model=self.model, config=config) as session:
            logger.info("Gemini Live session connected model=%s", self.model)
            audio_frames_sent = 0
            video_frames_sent = 0
            text_messages_sent = 0
            
            async def send_audio():
                nonlocal audio_frames_sent
                try:
                    while True:
                        chunk = await audio_input_queue.get()
                        audio_frames_sent += 1
                        if audio_frames_sent <= 3 or audio_frames_sent % 50 == 0:
                            logger.info(
                                "Sending audio chunk #%s to Gemini: %s bytes",
                                audio_frames_sent,
                                len(chunk),
                            )
                        await session.send_realtime_input(
                            audio=types.Blob(data=chunk, mime_type=f"audio/pcm;rate={self.input_sample_rate}")
                        )
                except asyncio.CancelledError:
                    logger.info("send_audio task cancelled after %s chunks", audio_frames_sent)

            async def send_video():
                nonlocal video_frames_sent
                try:
                    while True:
                        chunk = await video_input_queue.get()
                        video_frames_sent += 1
                        if video_frames_sent <= 3 or video_frames_sent % 20 == 0:
                            logger.info(
                                "Sending video frame #%s to Gemini: %s bytes",
                                video_frames_sent,
                                len(chunk),
                            )
                        await session.send_realtime_input(
                            video=types.Blob(data=chunk, mime_type="image/jpeg")
                        )
                except asyncio.CancelledError:
                    logger.info("send_video task cancelled after %s frames", video_frames_sent)

            async def send_text():
                nonlocal text_messages_sent
                try:
                    while True:
                        text = await text_input_queue.get()
                        text_messages_sent += 1
                        logger.info(
                            "Sending text #%s to Gemini: %s",
                            text_messages_sent,
                            text[:240],
                        )
                        await session.send_realtime_input(text=text)
                except asyncio.CancelledError:
                    logger.info("send_text task cancelled after %s messages", text_messages_sent)

            event_queue = asyncio.Queue()

            async def receive_loop():
                try:
                    while True:
                        async for response in session.receive():
                            logger.debug(f"Received response from Gemini: {response}")
                            server_content = response.server_content
                            tool_call = response.tool_call
                            
                            if server_content:
                                if server_content.model_turn:
                                    logger.info("Gemini model_turn received")
                                    for part in server_content.model_turn.parts:
                                        if part.inline_data:
                                            logger.debug(
                                                "Gemini audio response chunk bytes=%s",
                                                len(part.inline_data.data),
                                            )
                                            if inspect.iscoroutinefunction(audio_output_callback):
                                                await audio_output_callback(part.inline_data.data)
                                            else:
                                                audio_output_callback(part.inline_data.data)
                                
                                if server_content.input_transcription and server_content.input_transcription.text:
                                    logger.info(
                                        "Gemini input transcription: %s",
                                        server_content.input_transcription.text,
                                    )
                                    await event_queue.put({"type": "user", "text": server_content.input_transcription.text})
                                
                                if server_content.output_transcription and server_content.output_transcription.text:
                                    logger.info(
                                        "Gemini output transcription: %s",
                                        server_content.output_transcription.text,
                                    )
                                    await event_queue.put({"type": "gemini", "text": server_content.output_transcription.text})
                                
                                if server_content.turn_complete:
                                    logger.info("Gemini turn complete")
                                    await event_queue.put({"type": "turn_complete"})
                                
                                if server_content.interrupted:
                                    logger.info("Gemini output interrupted")
                                    if audio_interrupt_callback:
                                        if inspect.iscoroutinefunction(audio_interrupt_callback):
                                            await audio_interrupt_callback()
                                        else:
                                            audio_interrupt_callback()
                                    await event_queue.put({"type": "interrupted"})

                            if tool_call:
                                logger.info(
                                    "Gemini requested %s tool call(s)",
                                    len(tool_call.function_calls),
                                )
                                function_responses = []
                                for fc in tool_call.function_calls:
                                    func_name = fc.name
                                    args = fc.args or {}
                                    logger.info(
                                        "Tool call start name=%s id=%s args=%s",
                                        func_name,
                                        fc.id,
                                        args,
                                    )
                                    await event_queue.put(
                                        {
                                            "type": "tool_call_start",
                                            "name": func_name,
                                            "args": args,
                                        }
                                    )
                                    
                                    if func_name in self.tool_mapping:
                                        try:
                                            tool_func = self.tool_mapping[func_name]
                                            if inspect.iscoroutinefunction(tool_func):
                                                result = await tool_func(**args)
                                            else:
                                                loop = asyncio.get_running_loop()
                                                result = await loop.run_in_executor(None, lambda: tool_func(**args))
                                            logger.info(
                                                "Tool call success name=%s id=%s",
                                                func_name,
                                                fc.id,
                                            )
                                        except Exception as e:
                                            logger.exception(
                                                "Tool call failed name=%s id=%s",
                                                func_name,
                                                fc.id,
                                            )
                                            result = f"Error: {e}"
                                    else:
                                        logger.warning(
                                            "Tool call skipped unknown name=%s id=%s",
                                            func_name,
                                            fc.id,
                                        )
                                        result = {
                                            "ok": False,
                                            "message": f"Unknown tool: {func_name}",
                                        }
                                    
                                    model_result = (
                                        result.get("model_response", result)
                                        if isinstance(result, dict)
                                        else result
                                    )
                                    logger.info(
                                        "Tool response sizes name=%s id=%s browser_bytes=%s model_bytes=%s",
                                        func_name,
                                        fc.id,
                                        len(json.dumps(result, ensure_ascii=False).encode("utf-8"))
                                        if isinstance(result, dict)
                                        else 0,
                                        len(json.dumps(model_result, ensure_ascii=False).encode("utf-8"))
                                        if isinstance(model_result, dict)
                                        else 0,
                                    )
                                    function_responses.append(types.FunctionResponse(
                                        name=func_name,
                                        id=fc.id,
                                        response={"result": model_result}
                                    ))
                                    await event_queue.put({"type": "tool_call", "name": func_name, "args": args, "result": result})
                                
                                logger.info(
                                    "Sending %s tool response(s) back to Gemini",
                                    len(function_responses),
                                )
                                await session.send_tool_response(function_responses=function_responses)

                except Exception as e:
                    logger.exception("Gemini receive_loop failed")
                    await event_queue.put({"type": "error", "error": str(e)})
                finally:
                    logger.info("Gemini receive_loop finished")
                    await event_queue.put(None)

            send_audio_task = asyncio.create_task(send_audio())
            send_video_task = asyncio.create_task(send_video())
            send_text_task = asyncio.create_task(send_text())
            receive_task = asyncio.create_task(receive_loop())

            try:
                while True:
                    event = await event_queue.get()
                    if event is None:
                        logger.info("Gemini event queue closed")
                        break
                    if isinstance(event, dict) and event.get("type") == "error":
                        # Just yield the error event, don't raise to keep the stream alive if possible or let caller handle
                        logger.error("Gemini error event propagated: %s", event)
                        yield event
                        break 
                    yield event
            finally:
                logger.info("Gemini session cleanup starting")
                send_audio_task.cancel()
                send_video_task.cancel()
                send_text_task.cancel()
                receive_task.cancel()
