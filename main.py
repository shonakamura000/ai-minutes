import os
import requests
import pyaudio
import wave
import datetime
import time
import json
import argparse
import re
from dotenv import load_dotenv

# ========= .env 読み込み =========
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TRANSCRIPT_OUTPUT_PATH = os.getenv("TRANSCRIPT_OUTPUT_PATH", "transcripts")

# ========= 録音設定 =========
CHUNK = 4096
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

def record_audio_segment(duration=90, filename="audio_temp.wav"):
    """
    duration秒間の音声を録音して、WAVファイルとして保存する関数や。
    """
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                    input=True, frames_per_buffer=CHUNK)
    frames = []
    print(f"録音開始！（{duration}秒間）")
    for _ in range(0, int(RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)
    print("録音終了！")
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

def transcribe_audio(filename="audio_temp.wav"):
    """
    録音したWAVファイルをOpenAIのtranscription APIに送信して文字起こし結果を返す関数や。
    """
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    with open(filename, "rb") as f:
        files = {"file": f}
        data = {"model": "whisper-1", "language": "ja", "temperature": 0.0}
        response = requests.post("https://api.openai.com/v1/audio/transcriptions",
                                 headers=headers, files=files, data=data)
        response.raise_for_status()
        result = response.json()
        return result.get("text", "")

def format_transcript(text):
    """
    録音されたテキストを発言ごとに分割して、リストで返す関数や。
    日本語の場合、「。」を目安に分割する一例や。
    """
    # 「。」の後ろで分割し、空白は除去する
    utterances = re.split(r'(?<=。)', text)
    utterances = [u.strip() for u in utterances if u.strip()]
    return utterances

def save_transcript(meeting_title, transcript_data):
    """
    議事録の全データをJSONファイルとして保存する関数や。
    """
    if not os.path.exists(TRANSCRIPT_OUTPUT_PATH):
        os.makedirs(TRANSCRIPT_OUTPUT_PATH)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(TRANSCRIPT_OUTPUT_PATH, f"{meeting_title}_{timestamp}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(transcript_data, f, ensure_ascii=False, indent=4)
    print(f"議事録を保存したで: {filename}")
    return filename  # 保存したファイル名を返す

def summarize_transcript_with_gpt(transcript_data):
    """
    議事録データから全体のテキストを生成し、GPTに要約を依頼する関数や。
    """
    # 各セグメントの発言をタイムスタンプ付きで連結
    transcript_text = ""
    for segment in transcript_data["segments"]:
        transcript_text += f"[{segment['timestamp']}]\n"
        for utterance in segment["utterances"]:
            transcript_text += utterance + "\n"
    # GPT用のプロンプトを作成
    prompt = f"""以下の議事録をもとに、会議の要点をまとめた分かりやすい要約を日本語で作成してな。

    議事録内容:
    {transcript_text}
    """
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "あなたは会議の議事録から要約を作成するプロのアシスタントです。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 500
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
    response.raise_for_status()
    result = response.json()
    summary = result["choices"][0]["message"]["content"].strip()
    return summary

def main():
    # コマンドライン引数で会議タイトルとセグメントの録音時間を指定する
    parser = argparse.ArgumentParser(description="議事録作成アプリ")
    parser.add_argument("--title", type=str, required=True, help="会議のタイトルを入力してな")
    parser.add_argument("--segment", type=int, default=60, help="録音セグメントの秒数（デフォルト60秒）")
    args = parser.parse_args()
    
    meeting_title = args.title
    segment_duration = args.segment
    
    # 議事録の基本情報を記録
    transcript_data = {
        "meeting_title": meeting_title,
        "start_time": datetime.datetime.now().isoformat(),
        "segments": []
    }
    
    print(f"【{meeting_title}】の議事録作成ツールを開始するで。Ctrl+C で停止してな。")
    
    try:
        while True:
            segment_start = datetime.datetime.now()
            # 各セグメントの録音を実施
            record_audio_segment(duration=segment_duration, filename="audio_temp.wav")
            try:
                segment_transcript = transcribe_audio(filename="audio_temp.wav")
            except Exception as e:
                print(f"文字起こしエラー: {e}")
                segment_transcript = "[文字起こしエラー]"
            
            time_stamp = segment_start.strftime("%H:%M:%S")
            
            # 発言ごとに段落を分割する処理
            if segment_transcript != "[文字起こしエラー]":
                utterances = format_transcript(segment_transcript)
            else:
                utterances = [segment_transcript]
            
            transcript_data["segments"].append({
                "timestamp": time_stamp,
                "utterances": utterances
            })
            
            print(f"【{time_stamp}】の文字起こし結果:")
            for u in utterances:
                print(u)
    except KeyboardInterrupt:
        transcript_data["end_time"] = datetime.datetime.now().isoformat()
        # 議事録データを保存
        transcript_filename = save_transcript(meeting_title, transcript_data)
        
        # GPTに要約を依頼
        try:
            print("GPTに要約を依頼中や...")
            summary = summarize_transcript_with_gpt(transcript_data)
            transcript_data["summary"] = summary
            # 要約結果を別ファイルとしても保存する
            summary_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_filename = os.path.join(TRANSCRIPT_OUTPUT_PATH, f"{meeting_title}_summary_{summary_timestamp}.txt")
            with open(summary_filename, "w", encoding="utf-8") as f:
                f.write(summary)
            print("【要約】")
            print(summary)
        except Exception as e:
            print(f"要約作成エラー: {e}")
        print("議事録作成を終了したで。")

if __name__ == "__main__":
    main()