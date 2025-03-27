[![Watch Demo Video]](https://drive.google.com/file/d/1Z2PolJq512NwrvhNrW57QdfzCy0lhZoD/view)

# Real-Time Speech-to-Text Call Transcription and Streaming

## Overview
This project is a real-time Speech-to-Text (STT) system designed to transcribe live calls and provide summarized insights using AI. It integrates a VoIP calling framework with STT and AI-based summarization to enhance call analysis and automation.

Note: This project contains only python backend that works with asterisk.

## Main Idea
Asterisk runs a python script when a call placed. Using MixMonitor() application of asterisks, on going call recording will be mentained in a FIFO file. Which will be used by google's grpc protocol. The generated transcript will execute multiple openai requests asynchoronously. 

## Latency:
- Real time dialogue retrieval within **1-2 seconds**(google cloud stt).
- Realtime emoji and speaker dialogue temperature retrieval every **2 to 4 dialogues**, using openai.
- Rall transcript summarization within **2 to 3 seconds** after call ends.

## Features
- **Real-time call transcription** using Google Speech-to-Text API
- **Call handling and routing** via Asterisk and Vicidial
- **AI-powered transcript summarization** using OpenAI models
- **Automated workflow** for handling call data and generating insights

## Tech Stack & Tools
### 1. **Vicidial**
   - Open-source contact center solution
   - Manages outbound and inbound calls
   - Provides agent and campaign management

### 2. **Asterisk**
   - Open-source telephony framework
   - Handles call processing, SIP communication, and RTP streaming
   - Used for real-time call streaming to STT pipeline

### 3. **Python**
   - Orchestrates the STT and summarization workflow
   - Connects different components via APIs and sockets
   - Processes audio streams for transcription

### 4. **Google Speech-to-Text API**
   - Converts real-time call audio to text
   - Supports multiple languages and speaker diarization
   - Provides high accuracy for call transcriptions

### 5. **OpenAI API**
   - Summarizes transcribed call content
   - Extracts key points, action items, and sentiments
   - Provides structured insights from long conversations

## System Architecture
1. **Call Handling**: Asterisk receives and processes live calls.
2. **Audio Streaming**: Calls are streamed to the STT pipeline.
3. **Transcription**: Google Speech-to-Text API converts the audio into text.
4. **Summarization**: The transcribed text is processed via OpenAI for summarization.
5. **Storage & Insights**: The output is stored for further analysis and reporting.

## Deployment
1. **Setup Asterisk and Vicidial** for managing VoIP calls.
2. **Configure RTP streaming** for real-time audio transmission.
3. **Develop a Python pipeline** to process incoming audio and send requests to Google STT.
4. **Integrate OpenAI API** for summarizing transcriptions.
5. **Deploy the system** on a server for real-time call monitoring and insights.

## Future Enhancements
- Implement speaker identification
- Support for multi-language transcriptions
- Real-time keyword spotting and sentiment analysis

## Contributions
Contributions and improvements are welcome! Feel free to submit pull requests or report issues.

## License
This project is open-source and licensed under [MIT License](LICENSE).

