import os
import sys
import time
import google.cloud.speech as speech
from openai import OpenAI
import asyncio, json
import websockets
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import aiofiles
from openai import AsyncOpenAI
import ast
from dotenv import load_dotenv
from datetime import datetime
import pytz

load_dotenv()

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/var/lib/asterisk/agi-bin/doalog-ai-a21e352e56a2.json"
OPENAI_API_KEY = os.getenv("OPENAI_KEY","")



def connect_to_database():
    """Connect to MySQL database and return connection object."""
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "doalog"),
            password=os.getenv("DB_PASSWORD", "1234"),
            database=os.getenv("DB_NAME", "asterisk"),
        )
        if connection.is_connected():
            #     print("✅ Connected to MySQL database")
            return connection
    except Error as e:
        print(f"❌ Error connecting to MySQL: {e}")
        return None


def insert_call_transcript(data):
    """Insert call transcript data into the database."""
    connection_x = connect_to_database()
    if not connection_x:
        return

    try:
        cursor_x = connection_x.cursor()

        insert_query = """
        INSERT INTO call_transcripts (unique_id, caller_id, callee_id, start_time, end_time, status, final_transcript, json_data)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
        data['unique_id'], data['caller_id'], data['callee_id'], data['start_time'], data['end_time'], data['status'],
        data['final_transcript'], data['json_data'])
        cursor_x.execute(insert_query, values)
        connection_x.commit()

        print("✅ Data inserted successfully!")
    except Error as e:
        print(f"❌ Error inserting data: {e}")
    finally:
        cursor_x.close()
        connection_x.close()


def update_call_transcript(data):
    """Update an existing call transcript record in the database."""
    connection_y = connect_to_database()
    if not connection_y:
        return

    try:
        cursor_y = connection_y.cursor()

        update_query = """
        UPDATE call_transcripts
        SET caller_id = %s, callee_id = %s, start_time = %s, end_time = %s, 
            status = %s, final_transcript = %s, json_data = %s
        WHERE unique_id = %s
        """
        # print("unique_id:",data['unique_id'])
        values = (
            data['caller_id'], data['callee_id'], data['start_time'],
            data['end_time'], data['status'], data['final_transcript'],
            data['json_data'], data['unique_id']
        )

        cursor_y.execute(update_query, values)
        connection_y.commit()

        if cursor_y.rowcount > 0:
            print("✅ Record updated successfully!")
        else:
            print("⚠️ No record found with the given unique_id.")

    except Error as e:
        print(f"❌ Error updating data: {e}")
    finally:
        cursor_y.close()
        connection_y.close()


# Get the FIFO path from the dial plan
try:
    data = {}
    # Retrieve and assign each argument to variables
    data['fifo_path'] = sys.argv[1]  # Path to the FIFO file
    data['channel_type'] = sys.argv[2]
    data['unique_id'] = sys.argv[3]
    data['channel'] = sys.argv[4]  # Channel name or information
    data['caller_id'] = sys.argv[5]  # Caller ID/ANI
    data['callee_id'] = sys.argv[6]  # Dialed number
    data['server_ip'] = sys.argv[7]  # Server IP address
    data['originator_ip'] = sys.argv[8]  # Originator IP address
    data['start_time'] = sys.argv[9]  # Date and time of the call

    # Log the received parameters (optional)
    print(f"Data: {data}")

    # insert call information in database
    data['status'] = 'ongoing'
    data['end_time'] = None
    data['final_transcript'] = None
    data['json_data'] = None
    data['speaker'] = "client" if data['channel_type'] == "IN" else "agent"

    try:
        if data['speaker'] == "agent":
            insert_call_transcript(data)
    except Exception as e:
        print(f"❌ Error in storing call information: {e}")

    # channel_name = sys.argv[2]
    if not os.path.exists(data['fifo_path']):
        raise FileNotFoundError(f"FIFO path does not exist: {data['fifo_path']}")
except IndexError:
    print("❌ Error: FIFO path argument missing.")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error while retrieving FIFO path: {e}")
    sys.exit(1)

# Google STT setup
try:
    client = speech.SpeechClient()
except Exception as e:
    print(f"❌ Error initializing Google Speech Client: {e}")
    sys.exit(1)


# OPENAI internal function for topic summarization:
async def call_breakdown_summary(data, transcript):
    try:
        print("🚀Started processing call_breakdown summary with openai.")
        file_name = "/var/lib/asterisk/agi-bin/prompts/call_breakdown.txt"
        async with aiofiles.open(file_name, 'r') as file:
            PROMPT = await file.read()  # Async file read

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        completion = await client.chat.completions.create(  # Await OpenAI API response
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": f"transcript:{transcript}"}
            ]
        )

        output_json = completion.choices[0].message.content
        try:
            output_json = output_json.replace("json",'')
            output_json = output_json.replace("```",'')
            output_json = ast.literal_eval(output_json)  # Safely convert string to dict
            # print(output_json, type(output_json))  # Should be <class 'dict'>
        except Exception as e:
            output_json = {}

        json_data = json.loads(data.get("json_data"))
        json_data.update({"call_breakdown_summary": output_json})
        data["json_data"] = json.dumps(json_data)

        print(f"✅ Process completed successfully!: call_breakdown summarization using openai.")
        # print(output_json)
        function_name = "call_breakdown_summarization"
        return function_name, data, output_json

    except Exception as e:
        print(f"❌ Error during topicwise_summary: {e}")

# OPENAI internal function for transcript summarization:
async def transcript_summary(data, transcript):
    try:
        """Summarize the transcript for agent and client."""
        print("🚀Started processing topicwise summary with openai.")
        file_name = "/var/lib/asterisk/agi-bin/prompts/transcript_summary.txt"
        async with aiofiles.open(file_name, 'r') as file:
            PROMPT = await file.read()  # Async file read

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        completion = await client.chat.completions.create(  # Await OpenAI API response
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": f"transcript:{transcript}"}
            ]
        )

        output_json = completion.choices[0].message.content
        try:
            output_json = output_json.replace("json",'')
            output_json = output_json.replace("```",'')
            output_json = ast.literal_eval(output_json)  # Safely convert string to dict
            # print(output_json, type(output_json))  # Should be <class 'dict'>
        except Exception as e:
            output_json = {}
                

        json_data = json.loads(data.get("json_data"))
        json_data.update({"transcript_summary": output_json})
        data["json_data"] = json.dumps(json_data)

        print(f"✅ Process completed successfully!: transcript summarization using openai.")
        # print(output_json)
        function_name = "transcript_summarization"
        return function_name, data, output_json

    except Exception as e:
        print(f"❌ Error during transcript_summary: {e}")

# OPENAI internal function for feedback summarization:
async def feedback_summary(data, transcript):
    try:
        """Summarize the feedback from the conversation"""
        print("🚀Started processing feedback summary with openai.")
        file_name = "/var/lib/asterisk/agi-bin/prompts/feedback_summary.txt"
        async with aiofiles.open(file_name, 'r') as file:
            PROMPT = await file.read()  # Async file read

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        completion = await client.chat.completions.create(  # Await OpenAI API response
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": f"transcript:{transcript}"}
            ]
        )

        output_json = completion.choices[0].message.content
        try:
            output_json = output_json.replace("json",'')
            output_json = output_json.replace("```",'')
            output_json = ast.literal_eval(output_json)  # Safely convert string to dict
            # print(output_json, type(output_json))  # Should be <class 'dict'>
        except Exception as e:
            output_json = {}
        

        json_data = json.loads(data.get("json_data"))
        json_data.update({"feedback_summary": output_json})
        data["json_data"] = json.dumps(json_data)

        print(f"✅ Process completed successfully!: feedback summarization using openai.")
        # print(output_json)
        function_name = "feedback_summarization"
        return function_name, data, output_json

    except Exception as e:
        print(f"❌ Error during feedback_summary: {e}")


# OPENAI internal function for feedback summarization:
async def auto_fill(data, transcript):
    try:
        """Summarize the auto_fill from the conversation"""
        print("🚀Started processing auto_fill with openai.")
        file_name = "/var/lib/asterisk/agi-bin/prompts/auto_fill.txt"
        async with aiofiles.open(file_name, 'r') as file:
            PROMPT = await file.read()  # Async file read

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        completion = await client.chat.completions.create(  # Await OpenAI API response
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": f"transcript:{transcript}"}
            ]
        )

        output_json = completion.choices[0].message.content
        
        try:
            output_json = output_json.replace("null",'""')
            output_json = output_json.replace("json",'')
            output_json = output_json.replace("```",'')
            output_json = ast.literal_eval(output_json)  # Safely convert string to dict
            # print(output_json, type(output_json))  # Should be <class 'dict'>
        except Exception as e:
            print("❌ Auto fill response error:",e,output_json)
            output_json = {}

        json_data = json.loads(data.get("json_data"))
        json_data.update({"auto_fill": output_json})
        data["json_data"] = json.dumps(json_data)

        print(f"✅ Process completed successfully!: auto_fill using openai.")
        # print(output_json)
        function_name = "auto_fill_summarization"
        return function_name, data, output_json

    except Exception as e:
        print(f"❌ Error during auto_fill: {e}")


# OPENAI internal function for feedback summarization:
async def extract_meeting_info(data, transcript):
    try:
        """extract_meeting_info from the conversation"""
        print("🚀Started processing extract_meeting_info with openai.")
        file_name = "/var/lib/asterisk/agi-bin/prompts/extract_meeting_info.txt"
        async with aiofiles.open(file_name, 'r') as file:
            PROMPT = await file.read()  # Async file read

        
        # Define the timezone (e.g., 'UTC', 'America/New_York', 'Asia/Kolkata')
        timezone = pytz.timezone(os.getenv("TIME_ZONE"))

        # Get the current date and time in the specified timezone
        now = datetime.now(timezone)

        # Format the date, time, and timezone
        current_date = now.strftime("%d:%m:%Y")
        current_time = now.strftime("%H:%M")
        timezone_name = now.tzname()

        PROMPT = PROMPT.replace("{CURRENT_DATE}", current_date) \
                        .replace("{CURRENT_TIME}", current_time) \
                        .replace("{TIMEZONE}", timezone_name)

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        completion = await client.chat.completions.create(  # Await OpenAI API response
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": f"transcript:{transcript}"}
            ]
        )

        output_json = completion.choices[0].message.content
        
        try:
            output_json = output_json.replace("json",'')
            output_json = output_json.replace("```",'')
            output_json = ast.literal_eval(output_json)  # Safely convert string to dict
            # print(output_json, type(output_json))  # Should be <class 'dict'>
        except Exception as e:
            print("❌ extract meeting info response error:",e,output_json)
            output_json = {}

        json_data = json.loads(data.get("json_data"))
        json_data.update({"extract_meeting_info": output_json})
        data["json_data"] = json.dumps(json_data)

        print(f"✅ Process completed successfully!: extract_meeting_info using openai.")
        # print(output_json)
        function_name = "extract_meeting_info"
        return function_name, data, output_json

    except Exception as e:
        print(f"❌ Error during extract_meeting_info: {e}")


def stream_audio(fifo_path):
    try:
        with open(fifo_path, 'rb') as audio_stream:
            while True:
                audio_data = audio_stream.read(4096)  # Read in chunks
                if not audio_data:
                    break  # Stop if no more data
                yield speech.StreamingRecognizeRequest(audio_content=audio_data)
    except Exception as e:
        print(f"❌ Error while reading from FIFO: {e}")
        raise


# OPENAI(1st): speaker bifercation
def categorize_speakers(file_name):
    client = OpenAI(api_key=OPENAI_API_KEY)

    with open(file_name, 'r') as file:
        transcript = file.read()

    PROMPT = """ Your task is to categorize the transcipt between an agent and a client. give it in a conversation format. do not generate any additional information.
    """
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"""You are an AI assistant that processes conversation transcripts between an Agent and a Client. Your task is to assign speaker labels to each dialogue while keeping the original content unchanged. Do not add or remove any information. Use only the words from the input transcript.
            Instructions:
            Identify and label each line of dialogue as either Agent: or Client: based on conversational context.
            Ensure that the content remains unaltered—no extra words, summaries, or modifications.
            Return the response in a structured text format, preserving the original sequence.

            ###few-shots###
            user: transcript: Hello
            assistant: response: Agent: Hello.

            user: transcript: Hello how are you I'm good thanks how about you I am good too
            assistant: Agent: Hello, how are you?\nclient: I'm good, thanks. how about you?\nagent: I am good too.
            """},
            {"role": "user", "content": f"transcript:{transcript}"}
        ]
    )

    categorized_output = completion.choices[0].message.content

    file_name = f"/var/spool/asterisk/monitor/open_ai/{os.path.splitext(os.path.basename(data['fifo_path']))[0]}.txt"
    with open(file_name, 'w') as file:
        file.write(categorized_output)

    print(f"Speaker categorization saved to {file_name}")
    return categorized_output


# OPENAI(2nd): Call all openai request asynchronous
async def async_process_openai(data, transcript):
    """Run openai tasks concurrently and process results as they complete."""
    print("🚀Started processing async_process_openai.")
    tasks = [asyncio.create_task(call_breakdown_summary(data, transcript)),asyncio.create_task(transcript_summary(data, transcript)),
             asyncio.create_task(feedback_summary(data, transcript)),asyncio.create_task(auto_fill(data, transcript)),
             asyncio.create_task(extract_meeting_info(data, transcript))]

    for task in asyncio.as_completed(tasks):  # Process results as they complete
        result = await task
        function_name, data, output_json = result

        # update json with new topic summarizations
        print(f"📊Function {function_name} output:{output_json}")

        # send response to session
        response_json = json.dumps({"function_name": function_name, "result": output_json})
        await send_transcript_to_server(response_json, data['caller_id'])

        # update data in database
        update_call_transcript(data)

        print(f"✅ Async task completed successfully.")


# send response to server
async def send_transcript_to_server(response_data, call_id):
    uri = os.getenv("SOCKET_PORT", "localhost")  # WebSocket server URI

    try:
        # Connect to the WebSocket server
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket server")

            # Send initial message with call_id
            # call_id = "12345"  # Replace with the desired call_id
            # await websocket.send(json.dumps({"received_from": "Transcript side","call_id":"12345"}))
            print(f"Sent call_id: {call_id}")

            # Simulate sending a transcript after a delay
            await websocket.send(
                json.dumps({"received_from": "Transcript side", "call_id": call_id, "transcript": response_data}))
            print(f"Sent transcript: {response_data}")
            # await websocket.close()
            # Optionally, listen for any response from the server
            response = await websocket.recv()
            print(f"Received response from server: {response}")

    except Exception as e:
        print(f"❌ Error: sending transcript to server: {e}")


async def analyze_sentiment(dialogues, data):
    """Run openai tasks concurrently and process speaker sentiments."""
    try:
        PROMPT = """You are an expert in sentiment analysis, Based on the dialogues choose best sentiments from Happy, Curious, Angry. return the output in json format as describe below.
        Also set the tone temperature based on 1,2,3,4,5. 1 means speaker is happy and maintaing the repo. 5 max as angry.
        {"sentiment":<sentiment>,
        "temperature":<temperature>}"""

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        completion = await client.chat.completions.create(  # Await OpenAI API response
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": f"dialogues:{','.join(dialogues)}"}
            ]
        )

        output_json = completion.choices[0].message.content
        
        try:
            output_json = output_json.replace("json",'')
            output_json = output_json.replace("```",'')
            output_json = ast.literal_eval(output_json)  # Safely convert string to dict
            response = json.dumps({"function_name": "sentiment","speaker": data["speaker"], "result": output_json})
            await send_transcript_to_server(response,data['caller_id'])
        except Exception as e:
            print("❌ sentiment analysis response error:",e,output_json)

        return None

    except Exception as e:
        print(f"❌ Error during extract_meeting")


async def on_going_suggestions(data, output_file_mix):
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)

        with open(output_file_mix, 'r') as file:
            transcript = file.read()

        PROMPT = """ Your task is to categorize the transcipt between an agent and a client. give it in a conversation format. do not generate any additional information."""
    
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """You are an AI assistant that processes conversation transcripts between an Agent and a Client. Your task is to 
                identify the suggestions for {SPEAKER} based on the on going conversation. Identify only one among them. do not send list.
                
                Suggestions: "Keep going", "Service", "Price", "Attitude", "Voice Up", "More Energy".
                
                output json:
                {
                "suggestion":<suggestion_values>   
                }
                """.replace("{SPEAKER}",data["speaker"])},
                {"role": "user", "content": f"transcript:{transcript}"}
            ]
        )

        output_json = completion.choices[0].message.content

        try:
            output_json = output_json.replace("json",'')
            output_json = output_json.replace("```",'')
            output_json = ast.literal_eval(output_json)  # Safely convert string to dict
            response = json.dumps({"function_name": "on_going_suggestion","speaker": data["speaker"], "result": output_json})
            await send_transcript_to_server(response,data['caller_id'])
        except Exception as e:
            print("❌ on going suggestions response error:",e,output_json)

        return None

    except Exception as e:
        print(f"❌ Error during on going suggestions")

# Google API
def transcribe(data):
    try:
        fifo_path = data['fifo_path']
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=8000,
            language_code="en-US"
            # language_code="gu-IN",
        )

        streaming_config = speech.StreamingRecognitionConfig(config=config, interim_results=True)

        print(f"Processing call from: {fifo_path}")

        # output_file = f"/var/spool/asterisk/monitor/google/{os.path.splitext(os.path.basename(fifo_path))[0]}.txt"
        output_file_mix = f"/var/spool/asterisk/monitor/google/{data['unique_id']}_mix.txt"
        responses = client.streaming_recognize(streaming_config, stream_audio(fifo_path))

        processed_text = ""

        try:
            with open(output_file_mix, "x") as f:
                print("File created successfully!")
        except FileExistsError:
            print("File already exists!")

        # send unique id to server
        try:
            if data['speaker'] == "agent":
                response = json.dumps({"function_name": "set_lead_id", "result": {"unique_id":data['unique_id'],"phone_number":data["callee_id"]}})
                asyncio.run(send_transcript_to_server(response,data['caller_id']))

        except Exception as e:
            print("❌ error sending unique id to server:",e)

        batch_dialogues=[]
        dialogue_count = 0
        with open(output_file_mix, 'a') as f:
            for response in responses:
                for result in response.results:
                    # print(result.channel_tag)
                    transcript = result.alternatives[0].transcript
                    # print("transcript:",transcript)

                    if result.is_final:
                        print("Final transcript:", transcript)

                        # send final dialogue to front end
                        response_transcript = {"channel_type":data["channel_type"],"dialogue":transcript}
                        response_json = json.dumps({"function_name": "realtime", "result": response_transcript})
                        asyncio.run(send_transcript_to_server(response_json, data['caller_id']))

                        # Write the final transcript to the file
                        dialogue = f"{data['speaker']}:{transcript}\n"
                        f.write(dialogue)
                        f.flush()
                        processed_text += dialogue

                        # Add the dialogue to the batch
                        batch_dialogues.append(dialogue)
                        dialogue_count += 1

                        # Call OpenAI sentiment analysis every 2 dialogues
                        if dialogue_count % 2 == 0:
                            # Schedule sentiment analysis as a background task
                            asyncio.run(analyze_sentiment(batch_dialogues,data))
                            # Clear the batch for the next set of dialogues
                            batch_dialogues = []

                        if dialogue_count % 4 == 0:
                            # Schedule sentiment analysis as a background task
                            asyncio.run(on_going_suggestions(data, output_file_mix))
                            # Clear the batch for the next set of dialogues
                            batch_dialogues = [] 

        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print("full transcript:", processed_text)
        print(f"Transcript saved to: {output_file_mix}")

        # save full transcript in database:
        data['final_transcript'] = processed_text
        data['end_time'] = end_time


        if data['speaker'] == "client":
            return None
        
        # update record with full transcript
        update_call_transcript(data)
        
        mix_transcript=""
        # Get full transcript from mix file
        with open(output_file_mix, "r") as f:
            mix_transcript = f.read()  # Read entire file into a variable


        # call Open AI for bifercation
        json_data = {}
        if mix_transcript:
            transcript = mix_transcript

            # send categorized transcript to server
            response_json = json.dumps({"function_name": "transcript", "result": transcript})

            asyncio.run(send_transcript_to_server(response_json, data['caller_id']))
            print("Sent to server: transcript")

            # update json as bifercated transcript
            json_data.update({"transcript": transcript})

            # update json data with bifercation response
            data['json_data'] = json.dumps(json_data)
            update_call_transcript(data)

            # run other async openai funcations
            asyncio.run(async_process_openai(data, transcript))



    except Exception as e:
        print(f"❌ Error during transcription: {e}")
        raise


try:
    transcribe(data)
finally:
    try:
        if os.path.exists(data['fifo_path']):
            os.remove(data['fifo_path'])
            print(f"Cleaned up FIFO: {data['fifo_path']}")
    except Exception as e:
        print(f"❌ Error during FIFO cleanup: {e}")
